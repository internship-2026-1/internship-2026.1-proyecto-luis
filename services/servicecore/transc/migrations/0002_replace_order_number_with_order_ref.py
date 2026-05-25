import uuid

from django.db import migrations, models


def populate_order_ref(apps, schema_editor):
    Order = apps.get_model("transc", "Order")
    database_alias = schema_editor.connection.alias
    for order in Order.objects.using(database_alias).all():
        order.order_ref = uuid.uuid4()
        order.save(update_fields=["order_ref"], using=database_alias)


class Migration(migrations.Migration):
    dependencies = [
        ("transc", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="order_ref",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(populate_order_ref, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="order",
            name="order_ref",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.RemoveField(
            model_name="order",
            name="order_number",
        ),
    ]
