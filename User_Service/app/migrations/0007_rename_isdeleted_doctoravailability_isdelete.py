# Generated by Django 4.2.7 on 2025-03-25 09:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0006_rename_isdelete_doctoravailability_isdeleted'),
    ]

    operations = [
        migrations.RenameField(
            model_name='doctoravailability',
            old_name='isDeleted',
            new_name='isDelete',
        ),
    ]
