# Generated by Django 4.2.7 on 2025-03-08 08:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='doctoravailability',
            name='room_created',
            field=models.BooleanField(default=False),
        ),
    ]
