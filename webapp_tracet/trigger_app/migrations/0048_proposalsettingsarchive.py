# Generated by Django 5.1 on 2024-11-25 16:23

import django.contrib.postgres.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trigger_app', '0047_alter_observations_proposal_decision_id_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProposalSettingsArchive',
            fields=[
                ('id_version', models.CharField(help_text='Combination of proposal id and version (id-version)', max_length=30, primary_key=True, serialize=False)),
                ('id', models.IntegerField(help_text='Original ProposalSettings id')),
                ('streams', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=20), blank=True, default=list, help_text='List of streams for this proposal', size=None)),
                ('version', models.CharField(default='1.0.0', help_text='Version of the proposal settings', max_length=10, null=True)),
                ('proposal_id', models.CharField(help_text='A short identifier of the proposal of maximum lenth 16 charcters.', max_length=16, verbose_name='Proposal ID')),
                ('proposal_description', models.CharField(help_text='A brief description of the proposal. Only needs to be enough to distinguish it from the other proposals.', max_length=513)),
                ('priority', models.IntegerField(default=1, help_text='Set proposal processing priority (lower is better)')),
                ('testing', models.CharField(choices=[('PRETEND_REAL', 'Real events only (Pretend Obs)'), ('BOTH', 'Real events (Real Obs) and test events (Pretend Obs)'), ('REAL_ONLY', 'Real events only (Real Obs)')], default='REAL_ONLY', max_length=128, verbose_name='What events will this proposal trigger on?')),
                ('source_type', models.CharField(choices=[('GRB', 'Gamma-ray burst'), ('FS', 'Flare star'), ('NU', 'Neutrino'), ('GW', 'Gravitational wave')], max_length=3, verbose_name='What type of source will you trigger on?')),
                ('active', models.BooleanField(default=True, help_text='Indicates whether this proposal setting is currently active.')),
                ('created_at', models.DateTimeField(help_text='Time when this proposal was created')),
                ('updated_at', models.DateTimeField(help_text='Last time this proposal was updated')),
                ('event_telescope', models.ForeignKey(blank=True, help_text='The telescope that this proposal will accept at least one Event from before observing.', null=True, on_delete=django.db.models.deletion.SET_NULL, to='trigger_app.eventtelescope', to_field='name')),
                ('project_id', models.ForeignKey(help_text="This is the target telescopes's project ID that is used with a password to schedule observations.", on_delete=django.db.models.deletion.CASCADE, to='trigger_app.telescopeprojectid', verbose_name='Project ID')),
                ('telescope', models.ForeignKey(help_text='Telescope this proposal will observer with.', on_delete=django.db.models.deletion.CASCADE, to='trigger_app.telescope', to_field='name', verbose_name='Telescope name')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
