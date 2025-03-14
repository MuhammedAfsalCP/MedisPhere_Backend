# Generated by Django 4.2.7 on 2025-03-14 09:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0007_alter_doctoravailability_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='doctoravailability',
            name='slot',
            field=models.CharField(choices=[('09:00 am - 10:00 am', 'Nine Ten Am'), ('10:00 am - 11:00 am', 'Ten Eleven Am'), ('11:00 am - 12:00 pm', 'Eleven Twelve Am'), ('12:00 pm - 1:00 pm', 'Twelve One Pm'), ('1:00 pm - 2:00 pm', 'One Two Pm'), ('2:00 pm - 3:00 pm', 'Two Three Pm'), ('3:00 pm - 4:00 pm', 'Three Four Pm'), ('4:00 pm - 5:00 pm', 'Four Five Pm'), ('5:00 pm - 6:00 pm', 'Five Six Pm'), ('6:00 pm - 7:00 pm', 'Six Seven Pm'), ('7:00 pm - 8:00 pm', 'Seven Eight Pm'), ('8:00 pm - 9:00 pm', 'Eight Nine Pm')], help_text='Select the available time slot (each slot is one hour)', max_length=19),
        ),
    ]
