# Generated by Django 4.2.7 on 2025-03-05 06:01

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='doctoravailability',
            name='patient',
            field=models.ForeignKey(blank=True, limit_choices_to={'is_doctor': False}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='appointments', to=settings.AUTH_USER_MODEL),
        ),
    ]
