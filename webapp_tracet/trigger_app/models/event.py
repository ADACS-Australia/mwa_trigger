from django.db import models

from .constants import SOURCE_CHOICES


class EventGroup(models.Model):
    id = models.AutoField(primary_key=True)
    trig_id = models.CharField(max_length=64, unique=True)
    earliest_event_observed = models.DateTimeField(blank=True, null=True)
    latest_event_observed = models.DateTimeField(blank=True, null=True)
    ra = models.FloatField(blank=True, null=True)
    dec = models.FloatField(blank=True, null=True)
    ra_hms = models.CharField(max_length=64, blank=True, null=True)
    dec_dms = models.CharField(max_length=64, blank=True, null=True)
    pos_error = models.FloatField(blank=True, null=True)
    recieved_data = models.DateTimeField(auto_now_add=True, blank=True)
    source_type = models.CharField(max_length=3, choices=SOURCE_CHOICES, null=True)
    ignored = models.BooleanField(default=True)
    event_observed = models.DateTimeField(blank=True, null=True)
    source_name = models.CharField(max_length=128, blank=True, null=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        ordering = ["-id"]


class Event(models.Model):
    id = models.AutoField(primary_key=True)
    event_group_id = models.ForeignKey(
        EventGroup,
        on_delete=models.SET_NULL,
        related_name="voevent",
        blank=True,
        null=True,
    )
    trig_id = models.CharField(max_length=64, blank=True, null=True)
    self_generated_trig_id = models.BooleanField(default=True)
    telescope = models.CharField(max_length=64, blank=True, null=True)
    sequence_num = models.IntegerField(blank=True, null=True)
    event_type = models.CharField(max_length=64, blank=True, null=True)
    topic = models.CharField(max_length=64, blank=True, null=True)
    role = models.CharField(max_length=64, blank=True, null=True)
    duration = models.FloatField(blank=True, null=True)
    ra = models.FloatField(blank=True, null=True)
    dec = models.FloatField(blank=True, null=True)
    ra_hms = models.CharField(max_length=64, blank=True, null=True)
    dec_dms = models.CharField(max_length=64, blank=True, null=True)
    pos_error = models.FloatField(blank=True, null=True)
    recieved_data = models.DateTimeField(auto_now_add=True, blank=True)
    event_observed = models.DateTimeField(blank=True, null=True)
    xml_packet = models.CharField(max_length=10000)
    ignored = models.BooleanField(default=True)
    source_name = models.CharField(max_length=128, blank=True, null=True)
    source_type = models.CharField(max_length=3, choices=SOURCE_CHOICES, null=True)

    fermi_most_likely_index = models.FloatField(blank=True, null=True)
    fermi_detection_prob = models.FloatField(blank=True, null=True)
    swift_rate_signif = models.FloatField(blank=True, null=True)
    antares_ranking = models.IntegerField(blank=True, null=True)
    hess_significance = models.FloatField(blank=True, null=True)

    # LVC
    lvc_false_alarm_rate = models.CharField(max_length=64, blank=True, null=True)
    lvc_significant = models.BooleanField(default=False, blank=True, null=True)
    lvc_event_url = models.CharField(max_length=2025, blank=True, null=True)
    lvc_binary_neutron_star_probability = models.FloatField(blank=True, null=True)
    lvc_neutron_star_black_hole_probability = models.FloatField(blank=True, null=True)
    lvc_binary_black_hole_probability = models.FloatField(blank=True, null=True)
    lvc_terrestial_probability = models.FloatField(blank=True, null=True)
    lvc_includes_neutron_star_probability = models.FloatField(blank=True, null=True)
    lvc_retraction_message = models.CharField(max_length=1000, blank=True, null=True)
    lvc_skymap_fits = models.CharField(max_length=2026, blank=True, null=True)
    lvc_prob_density_tile = models.FloatField(blank=True, null=True)
    lvc_skymap_file = models.FileField(upload_to="skymaps/", blank=True, null=True)
    lvc_instruments = models.CharField(max_length=64, blank=True, null=True)
    lvc_false_alarm_rate = models.CharField(max_length=128, blank=True, null=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"Event(id={self.id}, event_group_id={self.event_group_id})"
