import xmlrpc.client

from django.conf import settings


class OdooConfigurationError(Exception):
    pass


class OdooClient:
    def __init__(self):
        self.url = settings.ODOO_URL.rstrip("/")
        self.db = settings.ODOO_DB
        self.username = settings.ODOO_USERNAME
        self.api_key = settings.ODOO_API_KEY
        self.product_model = settings.ODOO_PRODUCT_MODEL
        self.sku_field = settings.ODOO_SKU_FIELD
        self.price_field = settings.ODOO_PRICE_FIELD
        self.stock_field = settings.ODOO_STOCK_FIELD

        missing = [
            key for key, value in {
                "ODOO_URL": self.url,
                "ODOO_DB": self.db,
                "ODOO_USERNAME": self.username,
                "ODOO_API_KEY": self.api_key,
            }.items() if not value
        ]
        if missing:
            raise OdooConfigurationError(
                f"Missing Odoo configuration values: {', '.join(missing)}"
            )

        self.common_proxy = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.object_proxy = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
        self.uid = self.common_proxy.authenticate(self.db, self.username, self.api_key, {})
        if not self.uid:
            raise OdooConfigurationError("Failed to authenticate against Odoo.")

    def _execute(self, model, method, args=None, kwargs=None):
        return self.object_proxy.execute_kw(
            self.db,
            self.uid,
            self.api_key,
            model,
            method,
            args or [],
            kwargs or {},
        )

    def get_model_fields(self):
        return self._execute(
            self.product_model,
            "fields_get",
            [],
            {"attributes": ["string", "type"]},
        )

    def fetch_product(self, *, odoo_id=None, sku=None):
        if not odoo_id and not sku:
            raise ValueError("odoo_id or sku is required to fetch from Odoo.")

        domain = []
        if odoo_id:
            domain = [["id", "=", int(odoo_id)]]
        elif sku:
            domain = [[self.sku_field, "=", sku]]

        records = self._execute(
            self.product_model,
            "search_read",
            [domain],
            {
                "fields": [
                    "id",
                    "name",
                    self.sku_field,
                    self.price_field,
                    self.stock_field,
                    "active",
                ],
                "limit": 1,
            },
        )
        if not records:
            return None

        record = records[0]
        return {
            "odoo_id": str(record["id"]),
            "sku": record.get(self.sku_field) or sku,
            "name": record.get("name", ""),
            "base_price": record.get(self.price_field, 0),
            "stock": max(int(record.get(self.stock_field, 0) or 0), 0),
            "is_active": record.get("active", True),
            "metadata": {
                "source": "odoo",
                "odoo_model": self.product_model,
            },
        }

    def list_products(self, limit=20):
        records = self._execute(
            self.product_model,
            "search_read",
            [[]],
            {
                "fields": [
                    "id",
                    "name",
                    self.sku_field,
                    self.price_field,
                    self.stock_field,
                    "active",
                ],
                "limit": limit,
            },
        )
        return [
            {
                "odoo_id": str(record["id"]),
                "sku": record.get(self.sku_field),
                "name": record.get("name", ""),
                "base_price": record.get(self.price_field, 0),
                "stock": max(int(record.get(self.stock_field, 0) or 0), 0),
                "is_active": record.get("active", True),
            }
            for record in records
        ]

    def list_raw_products(self, limit=100, offset=0):
        fields_meta = self.get_model_fields()
        field_names = list(fields_meta.keys())
        records = self._execute(
            self.product_model,
            "search_read",
            [[]],
            {
                "fields": field_names,
                "limit": limit,
                "offset": offset,
            },
        )
        total = self._execute(
            self.product_model,
            "search_count",
            [[]],
        )
        return {
            "count": total,
            "limit": limit,
            "offset": offset,
            "fields": field_names,
            "results": records,
        }

    def update_product(self, odoo_id, updates):
        """
        Actualiza un producto en Odoo.
        
        Args:
            odoo_id: ID del producto en Odoo
            updates: Diccionario con los campos a actualizar (name, base_price)
        
        Returns:
            True si la actualización fue exitosa
        """
        if not odoo_id:
            raise ValueError("odoo_id is required to update a product in Odoo.")
        
        # Mapear los campos del sistema a los campos de Odoo
        odoo_updates = {}
        if "name" in updates:
            odoo_updates["name"] = updates["name"]
        if "base_price" in updates:
            odoo_updates[self.price_field] = updates["base_price"]
        
        if not odoo_updates:
            return True  # No hay nada que actualizar
        
        # Ejecutar la actualización en Odoo
        result = self._execute(
            self.product_model,
            "write",
            [[int(odoo_id)], odoo_updates],
        )
        
        return result