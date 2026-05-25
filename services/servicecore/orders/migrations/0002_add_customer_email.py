from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='customer_email',
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
    ]
