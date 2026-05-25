from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import Transaction
from orders.models import Order


class OrderSerializer(serializers.ModelSerializer):
    order_ref = serializers.UUIDField(read_only=True)

    class Meta:
        model = Order
        fields = '__all__'


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'


class TransactionCreateSerializer(serializers.Serializer):
    order = serializers.UUIDField()
    payment_reference = serializers.CharField(max_length=64)
    status = serializers.ChoiceField(choices=Transaction.Status.choices, default=Transaction.Status.PENDING)

    def validate_order(self, value):
        try:
            Order.objects.using('postgresql_db').get(id=value)
        except Order.DoesNotExist as exc:
            raise ValidationError(f"Orden con ID '{value}' no existe.") from exc
        return value

    def validate_payment_reference(self, value):
        if Transaction.objects.using('postgresql_db').filter(payment_reference=value).exists():
            raise ValidationError(f"Ya existe una transacción con payment_reference '{value}'.")
        return value

    def create(self, validated_data):
        order = Order.objects.using('postgresql_db').get(id=validated_data['order'])
        
        transaction = Transaction.objects.using('postgresql_db').create(
            order=order,
            payment_reference=validated_data['payment_reference'],
            status=validated_data.get('status', Transaction.Status.PENDING),
            gateway='system',  # gateway se asigna automáticamente
            amount=order.total_amount,  # amount se obtiene de la orden
        )

        if transaction.status == Transaction.Status.APPROVED:
            self._decrement_order_stock(order)

        return transaction

    def _decrement_order_stock(self, order):
        from catalog.models import Product

        for item in order.items.all():
            try:
                product = Product.objects.get_document_by_sku(item.product_sku)
            except Product.DoesNotExist:
                continue

            product.stock = max(int(product.stock or 0) - item.quantity, 0)
            product.save()
