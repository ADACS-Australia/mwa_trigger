# Generated by Django 4.0.4 on 2023-01-23 06:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trigger_app', '0014_event_lvc_skymap_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposaldecision',
            name='alt',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='proposaldecision',
            name='az',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
