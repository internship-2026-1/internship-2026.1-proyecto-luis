from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('transc', '0002_replace_order_number_with_order_ref'),
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Order',
        ),
        migrations.AlterField(
            model_name='transaction',
            name='order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='orders.order'),
        ),
    ]
