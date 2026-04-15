from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('apps', '0004_user_bio'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[('admin', 'Admin'), ('b2b', 'B2B'), ('b2c', 'B2C')],
                default='b2c',
                max_length=10,
            ),
        ),
    ]
