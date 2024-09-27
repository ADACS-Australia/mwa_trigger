from django.contrib.auth.models import User
from django.db import models

from .proposal import ProposalSettings


class AlertPermission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    proposal = models.ForeignKey(ProposalSettings, on_delete=models.CASCADE)
    alert = models.BooleanField(default=True)
    debug = models.BooleanField(default=False)
    approval = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user}_{self.proposal.id}_{self.proposal.telescope}_{self.proposal.project_id}_Alerts"


class UserAlerts(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    proposal = models.ForeignKey(ProposalSettings, on_delete=models.CASCADE)
    EMAIL = 0
    SMS = 1
    PHONE_CALL = 2
    TYPE_CHOICES = ((EMAIL, "Email"), (SMS, "SMS"), (PHONE_CALL, "Phone Call"))
    type = models.PositiveSmallIntegerField(choices=TYPE_CHOICES)
    address = models.CharField(max_length=64, blank=True, null=True)
    alert = models.BooleanField(default=True)
    debug = models.BooleanField(default=True)
    approval = models.BooleanField(default=True)