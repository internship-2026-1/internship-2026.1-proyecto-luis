import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('order_number', models.UUIDField(default=uuid.uuid4, unique=True, editable=False)),
                ('customer_id', models.UUIDField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('synced', 'Synced'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('currency', models.CharField(default='USD', max_length=10)),
                ('odoo_sale_order_id', models.CharField(blank=True, max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'orders_order',
                'ordering': ['-created_at'],
                'app_label': 'orders',
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_sku', models.CharField(max_length=100)),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('price_at_purchase', models.DecimalField(decimal_places=2, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='orders.order')),
            ],
            options={
                'db_table': 'orders_order_items',
                'app_label': 'orders',
            },
        ),
        migrations.CreateModel(
            name='IntegrationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status_code', models.CharField(max_length=20)),
                ('raw_request', models.JSONField(default=dict)),
                ('raw_response', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='integration_logs', to='orders.order')),
            ],
            options={
                'db_table': 'orders_integration_logs',
                'app_label': 'orders',
            },
        ),
    ]
