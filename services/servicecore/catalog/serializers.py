from rest_framework import serializers

from .models import Catalog, Product


class CatalogSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def create(self, validated_data):
        return Catalog.objects.create_document(**validated_data)


class ProductSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    catalog_id = serializers.CharField(required=False, allow_blank=True)
    odoo_id = serializers.CharField(required=False, allow_blank=True)
    sku = serializers.CharField(max_length=100)
    name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    base_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, write_only=True)
    stock = serializers.IntegerField(required=False, min_value=0)
    images = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
    )
    specifications = serializers.JSONField(required=False)
    is_active = serializers.BooleanField(required=False)
    attributes = serializers.JSONField(required=False)
    metadata = serializers.JSONField(required=False)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["price"] = data.get("base_price")
        return data

    def validate(self, attrs):
        if "base_price" not in attrs and "price" in attrs:
            attrs["base_price"] = attrs.pop("price")
        elif "price" in attrs:
            attrs.pop("price")
        return attrs

    def validate_catalog_id(self, value):
        if value in (None, ""):
            return ""
        try:
            Catalog.objects.get_document(value)
        except Catalog.DoesNotExist as exc:
            raise serializers.ValidationError("Catalog not found.") from exc
        return value

    def create(self, validated_data):
        return Product.objects.create_document(**validated_data)


class InternalProductSyncSerializer(serializers.Serializer):
    odoo_id = serializers.CharField(required=False, allow_blank=True)
    sku = serializers.CharField(max_length=100, required=False, allow_blank=True)
    name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    base_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, write_only=True)
    stock = serializers.IntegerField(required=False, min_value=0)
    is_active = serializers.BooleanField(required=False)
    metadata = serializers.JSONField(required=False)
    fetch_from_odoo = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if "base_price" not in attrs and "price" in attrs:
            attrs["base_price"] = attrs.pop("price")
        elif "price" in attrs:
            attrs.pop("price")
        fetch_from_odoo = attrs.get("fetch_from_odoo", False)
        if fetch_from_odoo and not attrs.get("sku") and not attrs.get("odoo_id"):
            raise serializers.ValidationError("Provide sku or odoo_id when fetch_from_odoo is true.")
        if not fetch_from_odoo and not attrs.get("sku"):
            raise serializers.ValidationError("sku is required.")
        return attrs


class ProductEnrichmentSerializer(serializers.Serializer):
    catalog_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True)
    images = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
    )
    specifications = serializers.JSONField(required=False)

    def validate_catalog_id(self, value):
        if value in (None, ""):
            return ""
        try:
            Catalog.objects.get_document(value)
        except Catalog.DoesNotExist as exc:
            raise serializers.ValidationError("Catalog not found.") from exc
        return value
