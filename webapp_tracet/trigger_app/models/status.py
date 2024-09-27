from django.db import models


class Status(models.Model):
    RUNNING = 0
    BROKEN = 1
    STOPPED = 2
    STATUS_CHOICES = ((RUNNING, "Running"), (BROKEN, "Broken"), (STOPPED, "Stopped"))
    name = models.CharField(max_length=64, blank=True, null=True, unique=True)
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES)