from decimal import Decimal

from bson import ObjectId
from django.db import models
from django.utils import timezone

from .mongo import get_catalog_collection, get_product_collection


def normalize_mongo_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: normalize_mongo_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_mongo_value(item) for item in value]
    return value


class CatalogManager(models.Manager):
    def create_document(self, **validated_data):
        catalog = self.model(**validated_data)
        catalog.save()
        return catalog

    def all_documents(self):
        collection = get_catalog_collection()
        return [self.model.from_document(document) for document in collection.find().sort("created_at", -1)]

    def get_document(self, catalog_id):
        collection = get_catalog_collection()
        document = collection.find_one({"_id": ObjectId(catalog_id)})
        if not document:
            raise self.model.DoesNotExist(f"Catalog with id {catalog_id} does not exist.")
        return self.model.from_document(document)


class ProductManager(models.Manager):
    def create_document(self, **validated_data):
        product = self.model(**validated_data)
        product.save()
        return product

    def upsert_document(self, sku, defaults):
        collection = get_product_collection()
        now = timezone.now()
        document = {
            "sku": sku,
            "updated_at": now,
            **defaults,
        }
        document = normalize_mongo_value(document)

        existing = collection.find_one({"sku": sku})
        if existing:
            collection.update_one({"_id": existing["_id"]}, {"$set": document})
            existing.update(document)
            return self.model.from_document(existing)

        document["created_at"] = now
        result = collection.insert_one(document)
        document["_id"] = result.inserted_id
        return self.model.from_document(document)

    def all_documents(self):
        collection = get_product_collection()
        return [self.model.from_document(document) for document in collection.find().sort("created_at", -1)]

    def get_document(self, product_id):
        collection = get_product_collection()
        document = collection.find_one({"_id": ObjectId(product_id)})
        if not document:
            raise self.model.DoesNotExist(f"Product with id {product_id} does not exist.")
        return self.model.from_document(document)

    def get_document_by_sku(self, sku):
        collection = get_product_collection()
        document = collection.find_one({"sku": sku})
        if not document:
            raise self.model.DoesNotExist(f"Product with sku {sku} does not exist.")
        return self.model.from_document(document)


class Product(models.Model):
    id = models.CharField(max_length=24, primary_key=True, editable=False)
    catalog_id = models.CharField(max_length=24, blank=True)
    odoo_id = models.CharField(max_length=100, blank=True)
    sku = models.CharField(max_length=100)
    name = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=0)
    images = models.JSONField(default=list, blank=True)
    specifications = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    attributes = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(editable=False, null=True, blank=True)
    updated_at = models.DateTimeField(editable=False, null=True, blank=True)

    objects = ProductManager()

    class Meta:
        app_label = 'catalog'
        managed = False
        db_table = 'catalog_products'

    def save(self, *args, **kwargs):
        collection = get_product_collection()
        now = timezone.now()
        document = self.to_document()
        document["updated_at"] = now

        if self.id:
            collection.update_one(
                {"_id": ObjectId(self.id)},
                {"$set": document},
                upsert=True,
            )
        else:
            document["created_at"] = now
            result = collection.insert_one(document)
            self.id = str(result.inserted_id)
            self.created_at = document["created_at"]

        self.updated_at = document["updated_at"]

    def delete(self, *args, **kwargs):
        if not self.id:
            return
        get_product_collection().delete_one({"_id": ObjectId(self.id)})

    def to_document(self):
        document = {
            "odoo_id": self.odoo_id,
            "sku": self.sku,
            "catalog_id": self.catalog_id,
            "name": self.name,
            "description": self.description,
            "base_price": float(self.base_price),
            "price": float(self.base_price),
            "stock": self.stock,
            "images": self.images or [],
            "specifications": self.specifications or {},
            "is_active": self.is_active,
            "attributes": self.attributes or {},
            "metadata": self.metadata or {},
        }
        if self.created_at:
            document["created_at"] = self.created_at
        if self.updated_at:
            document["updated_at"] = self.updated_at
        return document

    @classmethod
    def from_document(cls, document):
        return cls(
            id=str(document["_id"]),
            catalog_id=str(document.get("catalog_id", "")),
            odoo_id=str(document.get("odoo_id", "")),
            sku=document["sku"],
            name=document.get("name", ""),
            description=document.get("description", ""),
            base_price=Decimal(str(document.get("base_price", document.get("price", 0)))),
            stock=document.get("stock", 0),
            images=document.get("images", []),
            specifications=document.get("specifications", {}),
            is_active=document.get("is_active", True),
            attributes=document.get("attributes", {}),
            metadata=document.get("metadata", {}),
            created_at=document.get("created_at"),
            updated_at=document.get("updated_at"),
        )

    def __str__(self):
        return f"{self.sku} - {self.name}"


class Catalog(models.Model):
    id = models.CharField(max_length=24, primary_key=True, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(editable=False, null=True, blank=True)
    updated_at = models.DateTimeField(editable=False, null=True, blank=True)

    objects = CatalogManager()

    class Meta:
        app_label = 'catalog'
        managed = False
        db_table = 'catalogs'

    def save(self, *args, **kwargs):
        collection = get_catalog_collection()
        now = timezone.now()
        document = self.to_document()
        document["updated_at"] = now

        if self.id:
            collection.update_one(
                {"_id": ObjectId(self.id)},
                {"$set": document},
                upsert=True,
            )
        else:
            document["created_at"] = now
            result = collection.insert_one(document)
            self.id = str(result.inserted_id)
            self.created_at = document["created_at"]

        self.updated_at = document["updated_at"]

    def delete(self, *args, **kwargs):
        if not self.id:
            return
        get_catalog_collection().delete_one({"_id": ObjectId(self.id)})

    def to_document(self):
        document = {
            "name": self.name,
            "description": self.description,
        }
        if self.created_at:
            document["created_at"] = self.created_at
        if self.updated_at:
            document["updated_at"] = self.updated_at
        return document

    @classmethod
    def from_document(cls, document):
        return cls(
            id=str(document["_id"]),
            name=document["name"],
            description=document.get("description", ""),
            created_at=document.get("created_at"),
            updated_at=document.get("updated_at"),
        )

    def __str__(self):
        return self.name
