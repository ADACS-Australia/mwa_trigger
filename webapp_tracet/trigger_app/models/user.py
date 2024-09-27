from django.db import models


class ATCAUser(models.Model):
    id = models.AutoField(primary_key=True)
    httpAuthUsername = models.CharField(max_length=128)
    httpAuthPassword = models.CharField(max_length=128)
    