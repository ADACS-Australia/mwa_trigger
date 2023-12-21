# Generated by Django 4.0.4 on 2023-05-31 04:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("trigger_app", "0021_alter_cometlog_log_alter_event_lvc_event_url_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="proposalsettings",
            name="mwa_freqspecs",
            field=models.CharField(
                default="144,24",
                help_text="The frequency channels IDs for the MWA to observe at.",
                max_length=260,
                verbose_name="MWA frequency specifications",
            ),
        ),
        migrations.AlterField(
            model_name="proposalsettings",
            name="proposal_description",
            field=models.CharField(
                help_text="A brief description of the proposal. Only needs to be enough to distinguish it from the other proposals.",
                max_length=513,
            ),
        ),
        migrations.AlterField(
            model_name="telescopeprojectid",
            name="atca_email",
            field=models.CharField(
                blank=True,
                help_text="The email address of someone that was on the ATCA observing proposal. This is an authentication step only required for ATCA.",
                max_length=515,
                null=True,
                verbose_name="ATCA Proposal Email",
            ),
        ),
        migrations.AlterField(
            model_name="telescopeprojectid",
            name="description",
            field=models.CharField(
                help_text="A brief description of the project.", max_length=5000
            ),
        ),
        migrations.AlterField(
            model_name="telescopeprojectid",
            name="id",
            field=models.CharField(
                help_text="The project ID for the telescope used to automatically schedule observations.",
                max_length=125,
                primary_key=True,
                serialize=False,
                verbose_name="Telescope Project ID",
            ),
        ),
        migrations.AlterField(
            model_name="telescopeprojectid",
            name="password",
            field=models.CharField(
                help_text="The project password for the telescope used to automatically schedule observations.",
                max_length=2020,
                verbose_name="Telescope Project Password",
            ),
        ),
    ]
