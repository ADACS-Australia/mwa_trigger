from datetime import datetime, timedelta

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Count
from django.utils import timezone

from .constants import SOURCE_CHOICES, TRIGGER_ON
from .event import EventGroup
from .telescope import EventTelescope, Telescope, TelescopeProjectID


class ProposalSettings(models.Model):

    id = models.AutoField(primary_key=True)

    streams = ArrayField(
        models.CharField(max_length=20),
        default=list,  # This sets default as empty list: []
        blank=True,
        help_text="List of streams for this proposal",
    )
    version = models.CharField(
        max_length=10,
        default="1.0.0",
        null=True,
        help_text="Version of the proposal settings",
    )

    proposal_id = models.CharField(
        max_length=16,
        unique=True,
        verbose_name="Proposal ID",
        help_text="A short identifier of the proposal of maximum lenth 16 charcters.",
    )
    telescope = models.ForeignKey(
        Telescope,
        to_field="name",
        verbose_name="Telescope name",
        help_text="Telescope this proposal will observer with. If the telescope you want is not here add it on the admin page.",
        on_delete=models.CASCADE,
    )
    project_id = models.ForeignKey(
        TelescopeProjectID,
        to_field="id",
        verbose_name="Project ID",
        help_text="This is the target telescopes's project ID that is used with a password to schedule observations.",
        on_delete=models.CASCADE,
    )
    proposal_description = models.CharField(
        max_length=513,
        help_text="A brief description of the proposal. Only needs to be enough to distinguish it from the other proposals.",
    )

    priority = models.IntegerField(
        help_text="Set proposal processing priority (lower is better)", default=1
    )
    event_telescope = models.ForeignKey(
        EventTelescope,
        to_field="name",
        help_text="The telescope that this proposal will accept at least one Event from before observing. Leave blank if you want to accept all telescopes.",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    testing = models.CharField(
        default=TRIGGER_ON[2][0],
        choices=TRIGGER_ON,
        verbose_name="What events will this proposal trigger on?",
        null=False,
        max_length=128,
    )

    source_type = models.CharField(
        max_length=3,
        choices=SOURCE_CHOICES,
        verbose_name="What type of source will you trigger on?",
    )

    active = models.BooleanField(
        default=True,
        help_text="Indicates whether this proposal setting is currently active.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Time when this proposal was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Last time this proposal was updated"
    )

    code_link = models.CharField(
        max_length=2028,
        blank=True,
        null=True,
        help_text="Link to the code repository or documentation",
        default="",  # Empty default, will be set in save() method
    )

    def __str__(self):
        return f"{self.proposal_id}"

    def save(self, *args, **kwargs):
        if not self.code_link:
            self.code_link = (
                f"/shared/models/prop_{self.proposal_id.lower()}_{self.version}"
            )
        super().save(*args, **kwargs)

    def get_decision_statistics_all_time(self):
        decisions = (
            self.proposaldecision_set.filter(version=self.version)
            .values('decision')
            .annotate(count=Count('decision'))
        )
        stats = {'ignored': 0, 'error': 0, 'pending': 0, 'triggered': 0, 'canceled': 0}
        conversion = {
            'P': 'pending',
            'I': 'ignored',
            'E': 'error',
            'T': 'triggered',
            'C': 'canceled',
        }

        for decision in decisions:
            decision_code = decision['decision']
            if decision_code in conversion:
                stats[conversion[decision_code]] = decision['count']

        return stats

    def get_decision_statistics_for_duration(self, months=0):

        if months == 0:  # All time
            return self.get_decision_statistics_all_time()

        start_date = timezone.now() - timedelta(days=months * 30)
        decisions = (
            self.proposaldecision_set.filter(recieved_data__gte=start_date)
            .filter(version=self.version)
            .values('decision')
            .annotate(count=Count('decision'))
        )

        stats = {'ignored': 0, 'error': 0, 'pending': 0, 'triggered': 0, 'canceled': 0}
        conversion = {
            'P': 'pending',
            'I': 'ignored',
            'E': 'error',
            'T': 'triggered',
            'C': 'canceled',
        }

        for decision in decisions:
            decision_code = decision['decision']
            if decision_code in conversion:
                stats[conversion[decision_code]] = decision['count']

        return stats


class ProposalDecision(models.Model):
    id = models.AutoField(primary_key=True)
    P = "P"
    I = "I"
    E = "E"
    T = "T"
    C = "C"
    CHOICES = (
        (P, "Pending"),
        (I, "Ignored"),
        (E, "Error"),
        (T, "Triggered"),
        (C, "Canceled"),
    )
    decision = models.CharField(max_length=32, choices=CHOICES, default=P)
    decision_reason = models.CharField(max_length=2056, blank=True, null=True)

    proposal = models.ForeignKey(
        ProposalSettings, on_delete=models.CASCADE, blank=True, null=True
    )
    # proposal_id = models.IntegerField(blank=True, null=True)

    event_group_id = models.ForeignKey(
        EventGroup, on_delete=models.SET_NULL, blank=True, null=True
    )
    trig_id = models.CharField(max_length=64, blank=True, null=True)
    duration = models.FloatField(blank=True, null=True)
    ra = models.FloatField(blank=True, null=True)
    dec = models.FloatField(blank=True, null=True)
    alt = models.FloatField(blank=True, null=True)
    az = models.FloatField(blank=True, null=True)
    ra_hms = models.CharField(max_length=32, blank=True, null=True)
    dec_dms = models.CharField(max_length=32, blank=True, null=True)
    pos_error = models.FloatField(blank=True, null=True)
    recieved_data = models.DateTimeField(auto_now_add=True, blank=True)

    version = models.CharField(
        max_length=10,
        default="1.0.0",
        null=True,
        help_text="Version inherited from ProposalSettings",
    )

    def __str__(self):
        return str(self.id)

    def save(self, *args, **kwargs):
        if self.proposal and not self.version:
            self.version = self.proposal.version
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-id"]


class ProposalSettingsArchive(models.Model):

    id_version = models.CharField(
        primary_key=True,
        max_length=30,
        help_text="Combination of proposal id and version (id-version)",
    )

    id = models.IntegerField(
        help_text="Original ProposalSettings id",
    )

    streams = ArrayField(
        models.CharField(max_length=20),
        default=list,
        blank=True,
        help_text="List of streams for this proposal",
    )
    version = models.CharField(
        max_length=10,
        default="1.0.0",
        null=True,
        help_text="Version of the proposal settings",
    )
    proposal_id = models.CharField(
        max_length=16,
        verbose_name="Proposal ID",
        help_text="A short identifier of the proposal of maximum lenth 16 charcters.",
    )
    telescope = models.ForeignKey(
        Telescope,
        to_field="name",
        verbose_name="Telescope name",
        help_text="Telescope this proposal will observer with.",
        on_delete=models.CASCADE,
    )
    project_id = models.ForeignKey(
        TelescopeProjectID,
        to_field="id",
        verbose_name="Project ID",
        help_text="This is the target telescopes's project ID that is used with a password to schedule observations.",
        on_delete=models.CASCADE,
    )
    proposal_description = models.CharField(
        max_length=513,
        help_text="A brief description of the proposal. Only needs to be enough to distinguish it from the other proposals.",
    )
    code_link = models.CharField(
        max_length=2028,
        blank=True,
        null=True,
        help_text="Link to the code repository or documentation",
        default="",  # Empty default, will be set in save() method
    )
    priority = models.IntegerField(
        help_text="Set proposal processing priority (lower is better)", default=1
    )
    event_telescope = models.ForeignKey(
        EventTelescope,
        to_field="name",
        help_text="The telescope that this proposal will accept at least one Event from before observing.",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    testing = models.CharField(
        default=TRIGGER_ON[2][0],
        choices=TRIGGER_ON,
        verbose_name="What events will this proposal trigger on?",
        null=False,
        max_length=128,
    )
    source_type = models.CharField(
        max_length=3,
        choices=SOURCE_CHOICES,
        verbose_name="What type of source will you trigger on?",
    )
    active = models.BooleanField(
        default=True,
        help_text="Indicates whether this proposal setting is currently active.",
    )
    created_at = models.DateTimeField(help_text="Time when this proposal was created")
    updated_at = models.DateTimeField(help_text="Last time this proposal was updated")

    def save(self, *args, **kwargs):
        # Create the composite primary key
        if not self.id_version:
            self.id_version = f"{self.id}-{self.version}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.proposal_id} (v{self.version})"

    def get_decision_statistics_for_duration(self, months=0):
        if months == 0:  # All time
            return self.get_decision_statistics_all_time()

        start_date = timezone.now() - timedelta(days=months * 30)

        # Filter ProposalDecision objects by both id and version
        decisions = (
            ProposalDecision.objects.filter(
                proposal__id=self.id,
                version=self.version,
                recieved_data__gte=start_date,
            )
            .values('decision')
            .annotate(count=Count('decision'))
        )

        stats = {'ignored': 0, 'error': 0, 'pending': 0, 'triggered': 0, 'canceled': 0}
        conversion = {
            'P': 'pending',
            'I': 'ignored',
            'E': 'error',
            'T': 'triggered',
            'C': 'canceled',
        }

        for decision in decisions:
            decision_code = decision['decision']
            if decision_code in conversion:
                stats[conversion[decision_code]] = decision['count']

        return stats

    def get_decision_statistics_all_time(self):
        # Filter ProposalDecision objects by both id and version

        decisions = (
            ProposalDecision.objects.filter(proposal__id=self.id, version=self.version)
            .values('decision')
            .annotate(count=Count('decision'))
        )

        stats = {'ignored': 0, 'error': 0, 'pending': 0, 'triggered': 0, 'canceled': 0}
        conversion = {
            'P': 'pending',
            'I': 'ignored',
            'E': 'error',
            'T': 'triggered',
            'C': 'canceled',
        }

        for decision in decisions:
            decision_code = decision['decision']
            if decision_code in conversion:
                stats[conversion[decision_code]] = decision['count']

        return stats

    class Meta:
        ordering = ["-created_at"]
