# Generated by Django 5.0.6 on 2024-07-10 19:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_alter_txn_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='txn',
            name='is_error',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='txn',
            name='txreceipt_status',
            field=models.CharField(max_length=255),
        ),
    ]
