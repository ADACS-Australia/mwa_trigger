# Generated by Django 5.1 on 2024-12-04 03:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trigger_app', '0049_proposalsettings_code_link_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='topic',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
    ]
