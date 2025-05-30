# Generated by Django 4.2.7 on 2025-04-08 07:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Notification', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='notification',
            options={'ordering': ['-created_at']},
        ),
        migrations.AddField(
            model_name='notification',
            name='test_field',
            field=models.CharField(default='test', max_length=10),
        ),
        migrations.AlterField(
            model_name='notification',
            name='message',
            field=models.TextField(help_text='JSON string containing patient_email and text'),
        ),
        migrations.AlterField(
            model_name='notification',
            name='scheduled_at',
            field=models.DateTimeField(blank=True, help_text='Scheduled time for sending the notification', null=True),
        ),
        migrations.AlterField(
            model_name='notification',
            name='user_id',
            field=models.BigIntegerField(help_text='ID of the UserProfile from user_service'),
        ),
    ]
