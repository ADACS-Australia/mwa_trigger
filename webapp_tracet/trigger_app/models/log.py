from django.db import models


class CometLog(models.Model):
    id = models.AutoField(primary_key=True)
    log = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        ordering = ["-id"]