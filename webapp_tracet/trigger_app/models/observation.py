from django.db import models

from .event import Event
from .proposal import ProposalDecision
from .telescope import Telescope


class Observations(models.Model):
    trigger_id = models.CharField(max_length=128, primary_key=True)
    telescope = models.ForeignKey(
        Telescope,
        to_field="name",
        verbose_name="Telescope name",
        on_delete=models.CASCADE,
    )
    proposal_decision_id = models.ForeignKey(
        ProposalDecision, on_delete=models.SET_NULL, blank=True, null=True
    )
    website_link = models.URLField(max_length=2028)
    reason = models.CharField(max_length=2029, blank=True, null=True)
    mwa_sub_arrays = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    request_sent_at = models.DateTimeField(blank=True, null=True)
    mwa_sky_map_pointings = models.ImageField(
        upload_to="mwa_pointings", blank=True, null=True
    )
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, blank=True, null=True)
    mwa_response = models.JSONField(blank=True, null=True)
