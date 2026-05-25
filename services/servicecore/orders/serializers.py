import uuid

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from catalog.models import Product
from orders.models import IntegrationLog, Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['product_sku', 'quantity', 'price_at_purchase']


class IntegrationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationLog
        fields = ['id', 'status_code', 'raw_request', 'raw_response', 'created_at']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    integration_logs = IntegrationLogSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'customer_id',
            'status',
            'total_amount',
            'currency',
            'odoo_sale_order_id',
            'items',
            'integration_logs',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'order_number', 'status', 'odoo_sale_order_id', 'items', 'integration_logs', 'created_at', 'updated_at']


class OrderItemCreateSerializer(serializers.Serializer):
    product_sku = serializers.CharField(max_length=100)
    quantity = serializers.IntegerField(min_value=1)

    def validate_product_sku(self, value):
        try:
            Product.objects.get_document_by_sku(value)
        except Product.DoesNotExist as exc:
            raise ValidationError(f"Producto con SKU '{value}' no existe.") from exc
        return value

    def validate(self, attrs):
        product = Product.objects.get_document_by_sku(attrs['product_sku'])
        if attrs['quantity'] > product.stock:
            raise ValidationError(f"Stock insuficiente para el producto '{attrs['product_sku']}'.")
        return attrs


class OrderCreateSerializer(serializers.Serializer):
    products = OrderItemCreateSerializer(many=True)

    def validate_products(self, value):
        if not value:
            raise ValidationError("Debe proporcionar al menos un producto.")
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        customer_id = None

        if request is not None:
            raw_customer_id = (
                request.data.get('customer_id')
                or request.headers.get('X-Customer-Id')
                or request.headers.get('x-customer-id')
            )
            if raw_customer_id:
                try:
                    customer_id = uuid.UUID(raw_customer_id)
                except ValueError as exc:
                    raise ValidationError({'customer_id': 'Invalid UUID format.'}) from exc

        # Calcular total_amount sumando todos los productos
        total_amount = 0
        for item_data in validated_data['products']:
            product = Product.objects.get_document_by_sku(item_data['product_sku'])
            total_amount += product.base_price * item_data['quantity']

        order = Order.objects.using('postgresql_db').create(
            customer_id=customer_id,
            total_amount=total_amount,
            currency='USD',
            status=Order.Status.PENDING,
        )

        # Crear OrderItems para cada producto
        for item_data in validated_data['products']:
            product = Product.objects.get_document_by_sku(item_data['product_sku'])
            OrderItem.objects.using('postgresql_db').create(
                order=order,
                product_sku=product.sku,
                quantity=item_data['quantity'],
                price_at_purchase=product.base_price,
            )

        return order
