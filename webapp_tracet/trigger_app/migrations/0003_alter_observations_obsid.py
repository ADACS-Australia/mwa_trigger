# Generated by Django 4.0.4 on 2022-07-21 06:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trigger_app', '0002_alter_observations_obsid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='observations',
            name='obsid',
            field=models.CharField(max_length=128, primary_key=True, serialize=False),
        ),
    ]
