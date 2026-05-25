import uuid

from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SYNCED = 'synced', 'Synced'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    customer_id = models.UUIDField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='USD')
    odoo_sale_order_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'orders'
        db_table = 'orders_order'
        ordering = ['-created_at']

    def __str__(self):
        return str(self.order_number)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_sku = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'orders'
        db_table = 'orders_order_items'

    def __str__(self):
        return f'{self.product_sku} x {self.quantity}'


class IntegrationLog(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='integration_logs')
    status_code = models.CharField(max_length=20)
    raw_request = models.JSONField(default=dict)
    raw_response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'orders'
        db_table = 'orders_integration_logs'

    def __str__(self):
        return f'IntegrationLog(order={self.order_id}, status={self.status_code})'
