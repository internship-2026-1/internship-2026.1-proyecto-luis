from unittest.mock import patch

from bson import ObjectId
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from transc.models import Order


class FakeCursor:
    def __init__(self, documents):
        self.documents = list(documents)

    def sort(self, field, direction):
        reverse = direction == -1
        self.documents.sort(key=lambda document: document.get(field), reverse=reverse)
        return self.documents


class FakeInsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class FakeCollection:
    def __init__(self):
        self.documents = []

    def find(self):
        return FakeCursor(self.documents)

    def find_one(self, criteria):
        for document in self.documents:
            if all(document.get(key) == value for key, value in criteria.items()):
                return document.copy()
        return None

    def insert_one(self, document):
        saved = document.copy()
        saved["_id"] = ObjectId()
        self.documents.append(saved)
        return FakeInsertResult(saved["_id"])

    def update_one(self, criteria, update, upsert=False):
        for index, document in enumerate(self.documents):
            if all(document.get(key) == value for key, value in criteria.items()):
                updated = document.copy()
                updated.update(update.get("$set", {}))
                self.documents[index] = updated
                return

        if upsert:
            new_document = update.get("$set", {}).copy()
            new_document["_id"] = criteria.get("_id", ObjectId())
            self.documents.append(new_document)

    def delete_one(self, criteria):
        self.documents = [
            document
            for document in self.documents
            if not all(document.get(key) == value for key, value in criteria.items())
        ]


@override_settings(INTERNAL_SYNC_TOKEN="secret-sync-token")
class ProductSyncApiTests(TestCase):
    databases = {"default", "postgresql_db"}

    def setUp(self):
        self.client = APIClient()
        self.product_collection = FakeCollection()
        self.catalog_collection = FakeCollection()
        self.product_collection_patcher = patch("catalog.models.get_product_collection", return_value=self.product_collection)
        self.catalog_collection_patcher = patch("catalog.models.get_catalog_collection", return_value=self.catalog_collection)
        self.product_collection_patcher.start()
        self.catalog_collection_patcher.start()

    def tearDown(self):
        self.product_collection_patcher.stop()
        self.catalog_collection_patcher.stop()

    def test_stock_sync_preserves_images_and_specifications(self):
        sync_headers = {"HTTP_X_INTERNAL_TOKEN": "secret-sync-token"}

        create_response = self.client.post(
            "/api/v1/internal/sync-product/",
            {
                "sku": "SKU-001",
                "odoo_id": "44",
                "name": "Laptop",
                "base_price": "1500.00",
                "stock": 8,
            },
            format="json",
            **sync_headers,
        )
        self.assertEqual(create_response.status_code, 200)

        enrich_response = self.client.patch(
            "/api/v1/products/SKU-001/enrich/",
            {
                "description": "Equipo listo para marketing.",
                "images": ["https://cdn.example.com/laptop-1.jpg"],
                "specifications": {"ram": "16GB", "storage": "512GB"},
            },
            format="json",
        )
        self.assertEqual(enrich_response.status_code, 200)

        resync_response = self.client.post(
            "/api/v1/internal/sync-product/",
            {
                "sku": "SKU-001",
                "base_price": "1450.00",
                "stock": 3,
            },
            format="json",
            **sync_headers,
        )
        self.assertEqual(resync_response.status_code, 200)
        self.assertEqual(resync_response.data["stock"], 3)
        self.assertEqual(resync_response.data["images"], ["https://cdn.example.com/laptop-1.jpg"])
        self.assertEqual(resync_response.data["specifications"], {"ram": "16GB", "storage": "512GB"})
        self.assertEqual(resync_response.data["description"], "Equipo listo para marketing.")
        self.assertEqual(resync_response.data["base_price"], "1450.00")

    def test_sync_can_fetch_from_odoo(self):
        sync_headers = {"HTTP_X_INTERNAL_TOKEN": "secret-sync-token"}

        with patch("api.views.OdooClient") as mocked_client:
            mocked_client.return_value.fetch_product.return_value = {
                "sku": "SKU-ODOO",
                "odoo_id": "91",
                "name": "Producto Odoo",
                "base_price": 99.5,
                "stock": 11,
                "is_active": True,
                "metadata": {"source": "odoo"},
            }

            response = self.client.post(
                "/api/v1/internal/sync-product/",
                {
                    "sku": "SKU-ODOO",
                    "fetch_from_odoo": True,
                },
                format="json",
                **sync_headers,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["odoo_id"], "91")
        self.assertEqual(response.data["stock"], 11)


class OrderApiTests(TestCase):
    databases = {"default", "postgresql_db"}

    def setUp(self):
        self.client = APIClient()

    def test_order_creation_uses_order_ref_uuid(self):
        response = self.client.post(
            "/api/v1/orders/",
            {
                "customer_email": "buyer@example.com",
                "product_ids": ["SKU-001"],
                "items_snapshot": [{"sku": "SKU-001", "qty": 1}],
                "total_amount": "1450.00",
                "currency": "USD",
                "status": "pending",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn("order_ref", response.data)
        self.assertNotIn("order_number", response.data)

        order = Order.objects.using("postgresql_db").get(id=response.data["id"])
        self.assertEqual(str(order.order_ref), response.data["order_ref"])


class CatalogAndIntegrationApiTests(TestCase):
    databases = {"default", "postgresql_db"}

    def setUp(self):
        self.client = APIClient()
        self.product_collection = FakeCollection()
        self.catalog_collection = FakeCollection()
        self.product_collection_patcher = patch("catalog.models.get_product_collection", return_value=self.product_collection)
        self.catalog_collection_patcher = patch("catalog.models.get_catalog_collection", return_value=self.catalog_collection)
        self.product_collection_patcher.start()
        self.catalog_collection_patcher.start()

    def tearDown(self):
        self.product_collection_patcher.stop()
        self.catalog_collection_patcher.stop()

    def test_create_catalog_and_assign_it_to_product(self):
        catalog_response = self.client.post(
            "/api/v1/products/catalogs/",
            {
                "name": "Catalogo verano 2026",
                "description": "Coleccion principal",
            },
            format="json",
        )
        self.assertEqual(catalog_response.status_code, 201)

        product_response = self.client.post(
            "/api/v1/products/",
            {
                "sku": "SKU-CAT-1",
                "name": "Producto catalogado",
                "base_price": "25.00",
                "stock": 4,
                "catalog_id": catalog_response.data["id"],
            },
            format="json",
        )
        self.assertEqual(product_response.status_code, 201)
        self.assertEqual(product_response.data["catalog_id"], catalog_response.data["id"])

    def test_update_product_by_id(self):
        create_response = self.client.post(
            "/api/v1/products/",
            {
                "sku": "SKU-UPD-1",
                "name": "Base",
                "base_price": "10.00",
                "stock": 1,
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)

        response = self.client.put(
            f"/api/v1/products/products/{create_response.data['id']}/",
            {
                "price": "12.50",
                "stock": 9,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["base_price"], "12.50")
        self.assertEqual(response.data["stock"], 9)

    def test_integrate_products_matches_reference_flow(self):
        with patch("api.views.OdooClient") as mocked_client:
            mocked_client.return_value.list_raw_products.return_value = {
                "count": 2,
                "limit": 100,
                "offset": 0,
                "fields": ["id", "default_code", "name", "qty_available", "list_price", "active"],
                "results": [
                    {
                        "id": 1,
                        "default_code": "SKU-001",
                        "name": "Producto 1",
                        "qty_available": 10,
                        "list_price": 99.99,
                        "active": True,
                    },
                    {
                        "id": 2,
                        "default_code": "SKU-002",
                        "name": "Producto 2",
                        "qty_available": 5,
                        "list_price": 49.50,
                        "active": True,
                    },
                ],
            }

            response = self.client.post("/api/v1/integrate/products/", {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "Integración completada")
        self.assertEqual(response.data["created"], 2)
        self.assertEqual(response.data["updated"], 0)
