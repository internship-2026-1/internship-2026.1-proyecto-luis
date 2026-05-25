from catalog.models import Catalog, Product


SYNC_FIELDS = {
    "odoo_id",
    "sku",
    "catalog_id",
    "name",
    "base_price",
    "stock",
    "is_active",
    "metadata",
}

ENRICH_FIELDS = {
    "catalog_id",
    "description",
    "images",
    "specifications",
}


def sync_product(payload):
    sku = payload["sku"]
    defaults = {field: payload[field] for field in SYNC_FIELDS if field in payload}
    return Product.objects.upsert_document(sku=sku, defaults=defaults)


def enrich_product(sku, payload):
    product = Product.objects.get_document_by_sku(sku)
    updates = {field: payload[field] for field in ENRICH_FIELDS if field in payload}
    for field, value in updates.items():
        setattr(product, field, value)
    product.save()
    return product


def update_product_by_id(product_id, payload):
    from catalog.odoo import OdooClient, OdooConfigurationError
    
    product = Product.objects.get_document(product_id)
    updates = {field: payload[field] for field in (SYNC_FIELDS | ENRICH_FIELDS) if field in payload}
    
    # Si el producto tiene odoo_id y se están actualizando name o base_price, sincronizar con Odoo
    if product.odoo_id and ("name" in updates or "base_price" in updates):
        try:
            odoo_client = OdooClient()
            odoo_updates = {}
            if "name" in updates:
                odoo_updates["name"] = updates["name"]
            if "base_price" in updates:
                odoo_updates["base_price"] = updates["base_price"]
            
            odoo_client.update_product(product.odoo_id, odoo_updates)
        except (OdooConfigurationError, Exception) as e:
            # Log el error pero no fallar la actualización local
            print(f"Warning: Failed to sync product {product_id} to Odoo: {str(e)}")
    
    for field, value in updates.items():
        setattr(product, field, value)
    product.save()
    return product


def create_catalog(payload):
    return Catalog.objects.create_document(**payload)
