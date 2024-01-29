# Generated by Django 4.0.4 on 2023-05-19 03:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "trigger_app",
            "0017_alter_proposalsettings_start_observation_at_high_sensitivity",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="cometlog",
            name="log",
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
        migrations.AlterField(
            model_name="event",
            name="lvc_event_url",
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
        migrations.AlterField(
            model_name="event",
            name="lvc_skymap_fits",
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
        migrations.AlterField(
            model_name="observations",
            name="reason",
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
        migrations.AlterField(
            model_name="observations",
            name="website_link",
            field=models.URLField(max_length=512),
        ),
    ]
