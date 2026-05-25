from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import AuthenticationFailed, NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Catalog, Product
from catalog.odoo import OdooClient, OdooConfigurationError
from catalog.serializers import (
    CatalogSerializer,
    InternalProductSyncSerializer,
    ProductEnrichmentSerializer,
    ProductSerializer,
)
from catalog.services import create_catalog, enrich_product, sync_product, update_product_by_id
from orders.models import Order
from orders.serializers import OrderCreateSerializer, OrderSerializer
from orders.tasks import sync_order_to_odoo
from transc.models import Transaction
from transc.serializers import TransactionCreateSerializer, TransactionSerializer


@api_view(['GET'])
def health_check(request):
    return Response({
        "success": "True",
        "message": "El servicio está funcionando correctamente.",
        "data": {
            "service": "ServiceCore",
            "health": "ok"
        },
        "status": 200
    }, status=status.HTTP_200_OK)


class ProductListCreateView(APIView):
    def get(self, request):
        serializer = ProductSerializer(Product.objects.all_documents(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)


def validate_internal_token(request):
    expected_token = settings.INTERNAL_SYNC_TOKEN
    if not expected_token:
        raise AuthenticationFailed("INTERNAL_SYNC_TOKEN is not configured.")

    provided_token = request.headers.get("X-Internal-Token")
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        provided_token = auth_header.split(" ", 1)[1]

    if provided_token != expected_token:
        raise AuthenticationFailed("Invalid internal token.")


class InternalProductSyncView(APIView):
    def post(self, request):
        validate_internal_token(request)
        serializer = InternalProductSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        if payload.pop("fetch_from_odoo", False):
            try:
                odoo_product = OdooClient().fetch_product(
                    odoo_id=payload.get("odoo_id"),
                    sku=payload.get("sku"),
                )
            except OdooConfigurationError as exc:
                raise ValidationError({"odoo": str(exc)}) from exc

            if not odoo_product:
                raise NotFound("Product was not found in Odoo.")

            payload = odoo_product

        product = sync_product(payload)
        return Response(ProductSerializer(product).data, status=status.HTTP_200_OK)


class ProductEnrichmentView(APIView):
    def patch(self, request, sku):
        serializer = ProductEnrichmentSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            product = enrich_product(sku, serializer.validated_data)
        except Product.DoesNotExist as exc:
            raise NotFound("Product was not found.") from exc

        return Response(ProductSerializer(product).data, status=status.HTTP_200_OK)


class OdooProductListView(APIView):
    def get(self, request):
        validate_internal_token(request)
        try:
            limit = int(request.query_params.get("limit", 20))
        except ValueError as exc:
            raise ValidationError({"limit": "Must be an integer."}) from exc

        try:
            products = OdooClient().list_products(limit=limit)
        except OdooConfigurationError as exc:
            raise ValidationError({"odoo": str(exc)}) from exc

        return Response(products, status=status.HTTP_200_OK)


class OdooRawProductListView(APIView):
    def get(self, request):
        try:
            limit = int(request.query_params.get("limit", 100))
            offset = int(request.query_params.get("offset", 0))
        except ValueError as exc:
            raise ValidationError({"pagination": "limit and offset must be integers."}) from exc

        try:
            payload = OdooClient().list_raw_products(limit=limit, offset=offset)
        except OdooConfigurationError as exc:
            raise ValidationError({"odoo": str(exc)}) from exc

        return Response(payload, status=status.HTTP_200_OK)


class IntegrateProductsView(APIView):
    def post(self, request):
        try:
            raw_products = OdooClient().list_raw_products(
                limit=int(request.data.get("limit", 100)),
                offset=int(request.data.get("offset", 0)),
            )
        except ValueError as exc:
            raise ValidationError({"pagination": "limit and offset must be integers."}) from exc
        except OdooConfigurationError as exc:
            raise ValidationError({"odoo": str(exc)}) from exc

        created = 0
        updated = 0
        for record in raw_products["results"]:
            sku = record.get(settings.ODOO_SKU_FIELD) or record.get("barcode") or ""
            if not sku:
                continue

            payload = {
                "odoo_id": str(record.get("id", "")),
                "sku": sku,
                "name": record.get("name", "") or sku,
                "base_price": record.get(settings.ODOO_PRICE_FIELD, 0) or 0,
                "stock": max(int(record.get(settings.ODOO_STOCK_FIELD, 0) or 0), 0),
                "is_active": record.get("active", True),
                "metadata": {
                    "source": "odoo",
                    "raw_record": record,
                },
            }

            existed = True
            try:
                Product.objects.get_document_by_sku(sku)
            except Product.DoesNotExist:
                existed = False

            sync_product(payload)
            if existed:
                updated += 1
            else:
                created += 1

        return Response(
            {
                "message": "Integración completada",
                "created": created,
                "updated": updated,
                "total": raw_products["count"],
            },
            status=status.HTTP_200_OK,
        )


class CatalogListCreateView(APIView):
    def get(self, request):
        serializer = CatalogSerializer(Catalog.objects.all_documents(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CatalogSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        catalog = create_catalog(serializer.validated_data)
        return Response(CatalogSerializer(catalog).data, status=status.HTTP_201_CREATED)


class CatalogDetailView(APIView):
    def delete(self, request, catalog_id):
        try:
            catalog = Catalog.objects.get_document(catalog_id)
            catalog.delete()
            return Response(
                {"message": "Catálogo eliminado correctamente"},
                status=status.HTTP_200_OK
            )
        except Catalog.DoesNotExist as exc:
            raise NotFound("Catálogo no encontrado.") from exc


class ProductDetailView(APIView):
    def get(self, request, product_id):
        try:
            product = Product.objects.get_document(product_id)
        except Product.DoesNotExist as exc:
            raise NotFound("Product was not found.") from exc
        return Response(ProductSerializer(product).data, status=status.HTTP_200_OK)

    def put(self, request, product_id):
        return self._update(request, product_id)

    def patch(self, request, product_id):
        return self._update(request, product_id)

    def _update(self, request, product_id):
        serializer = ProductSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            product = update_product_by_id(product_id, serializer.validated_data)
        except Product.DoesNotExist as exc:
            raise NotFound("Product was not found.") from exc

        return Response(ProductSerializer(product).data, status=status.HTTP_200_OK)


class OrderListCreateView(APIView):
    def get(self, request):
        # Obtener el customer_id del header
        customer_id = request.headers.get('x-customer-id')
        
        # Debug
        print(f"OrderListCreateView - customer_id from header: {customer_id}")
        print(f"OrderListCreateView - all headers: {dict(request.headers)}")
        
        # Si no hay customer_id, retornar todas las órdenes (para admins)
        if customer_id:
            orders = Order.objects.using('postgresql_db').filter(customer_id=customer_id)
            print(f"Filtering orders by customer_id: {customer_id}, found: {orders.count()}")
        else:
            orders = Order.objects.using('postgresql_db').all()
            print(f"Returning all orders: {orders.count()}")
        
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class TransactionListCreateView(APIView):
    def get(self, request):
        transactions = Transaction.objects.using('postgresql_db').select_related('order').all()
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = TransactionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transaction = serializer.save()
        
        if transaction.status == Transaction.Status.APPROVED:
            sync_order_to_odoo.delay(str(transaction.order.id))
        
        return Response(TransactionSerializer(transaction).data, status=status.HTTP_201_CREATED)
