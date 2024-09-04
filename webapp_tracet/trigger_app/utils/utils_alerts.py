import logging
import os

import numpy as np
from astropy import units as u
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.time import Time
from django.conf import settings
from django.core.mail import send_mail
from trigger_app.models import AlertPermission, Event, Observations, UserAlerts
from twilio.rest import Client

logger = logging.getLogger(__name__)

account_sid = os.environ.get("TWILIO_ACCOUNT_SID", None)
auth_token = os.environ.get("TWILIO_AUTH_TOKEN", None)
my_number = os.environ.get("TWILIO_PHONE_NUMBER", None)


def send_all_alerts(trigger_bool, debug_bool, pending_bool, proposal_decision_model):
    """ """
    # Work out all the telescopes that observed the event
    logger.info(
        f"Work out all the telescopes that observed the event {trigger_bool, debug_bool, pending_bool, proposal_decision_model}"
    )
    voevents = Event.objects.filter(
        event_group_id=proposal_decision_model.event_group_id
    )
    telescopes = []
    for voevent in voevents:
        telescopes.append(voevent.telescope)
    # Make sure they are unique and put each on a new line
    telescopes = ", ".join(list(set(telescopes)))

    # Work out when the source will go below the horizon
    telescope = proposal_decision_model.proposal.telescope
    location = EarthLocation(
        lon=telescope.lon * u.deg,
        lat=telescope.lat * u.deg,
        height=telescope.height * u.m,
    )
    if proposal_decision_model.ra and proposal_decision_model.dec:
        obs_source = SkyCoord(
            proposal_decision_model.ra,
            proposal_decision_model.dec,
            # equinox='J2000',
            unit=(u.deg, u.deg),
        )
        # Convert from RA/Dec to Alt/Az
        # 24 hours in 5 min increments
        delta_24h = np.linspace(0, 1440, 288) * u.min
        next_24h = obstime = Time.now() + delta_24h
        obs_source_altaz = obs_source.transform_to(
            AltAz(obstime=next_24h, location=location)
        )
        # capture circumpolar source case
        set_time_utc = None
        for altaz, time in zip(obs_source_altaz, next_24h):
            if altaz.alt.deg < 1.0:
                # source below horizon so record time
                set_time_utc = time
                break

    # Get all admin alert permissions for this project
    logger.info("Get all admin alert permissions for this project")
    alert_permissions = AlertPermission.objects.filter(
        proposal=proposal_decision_model.proposal
    )
    for ap in alert_permissions:
        # Grab user
        user = ap.user
        user_alerts = UserAlerts.objects.filter(
            user=user, proposal=proposal_decision_model.proposal
        )

        # Send off the alerts of types user defined
        for ua in user_alerts:
            # Check if user can recieve each type of alert
            # Trigger alert
            if ap.alert and ua.alert and trigger_bool:
                subject = f"TraceT {proposal_decision_model.proposal.proposal_id}: {proposal_decision_model.proposal.telescope_id} TRIGGERING on {telescopes} {proposal_decision_model.event_group_id.source_type}"
                message_type_text = f"Tracet scheduled the following {proposal_decision_model.proposal.telescope} observations:\n"
                # Send links for each observation
                obs = Observations.objects.filter(
                    proposal_decision_id=proposal_decision_model
                )
                for ob in obs:
                    message_type_text += f"{ob.website_link}\n"
                try:
                    send_alert_type(
                        ua.type,
                        ua.address,
                        subject,
                        message_type_text,
                        proposal_decision_model,
                        telescopes,
                        set_time_utc,
                    )
                except Exception as e:
                    logger.error(f"Twillio error message: {e}")

            # Debug Alert
            if ap.debug and ua.debug and debug_bool:
                subject = f"TraceT {proposal_decision_model.proposal.proposal_id}: {proposal_decision_model.proposal.telescope_id} INFO on {telescopes} {proposal_decision_model.event_group_id.source_type}"
                message_type_text = f"This is a debug notification from TraceT."
                try:
                    send_alert_type(
                        ua.type,
                        ua.address,
                        subject,
                        message_type_text,
                        proposal_decision_model,
                        telescopes,
                        set_time_utc,
                    )
                except Exception as e:
                    logger.error(f"Twillio error message: {e}")

            # Pending Alert
            if ap.approval and ua.approval and pending_bool:
                subject = f"TraceT {proposal_decision_model.proposal.proposal_id}: {proposal_decision_model.proposal.telescope_id} PENDING on {telescopes} {proposal_decision_model.event_group_id.source_type}"
                message_type_text = f"HUMAN INTERVENTION REQUIRED! TraceT is unsure about the following event."
                try:
                    send_alert_type(
                        ua.type,
                        ua.address,
                        subject,
                        message_type_text,
                        proposal_decision_model,
                        telescopes,
                        set_time_utc,
                    )
                except Exception as e:
                    logger.error(f"Twillio error message: {e}")


def send_alert_type(
    alert_type,
    address,
    subject,
    message_type_text,
    proposal_decision_model,
    telescopes,
    set_time_utc,
):
    # Set up twillo client for SMS and calls
    client = Client(account_sid, auth_token)

    # Set up message text
    message_text = f"""{message_type_text}

Event Details are:
TraceT proposal:      {proposal_decision_model.proposal.proposal_id}
Detected by: {telescopes}
Event Type:  {proposal_decision_model.event_group_id.source_type}
Duration:    {proposal_decision_model.duration}
RA:          {proposal_decision_model.ra_hms} hours
Dec:         {proposal_decision_model.dec_dms} deg
Error Rad:   {proposal_decision_model.pos_error} deg
Event observed (UTC): {proposal_decision_model.event_group_id.earliest_event_observed}
Set time (UTC):       {set_time_utc}

Decision log:
{proposal_decision_model.decision_reason}

Proposal decision can be seen here:
https://mwa-trigger.duckdns.org/proposal_decision_details/{proposal_decision_model.id}/
"""

    if alert_type == 0:
        # Send an email
        logger.info("Send an email")
        send_mail(
            subject,
            message_text,
            settings.EMAIL_HOST_USER,
            [address],
            # fail_silently=False,
        )
    elif alert_type == 1:
        # Send an SMS
        logger.info("Send an SMS")
        message = client.messages.create(
            to=address,
            from_=my_number,
            body=message_text,
        )
    elif alert_type == 2:
        # Make a call
        logger.info("Make a call")
        call = client.calls.create(
            url="http://demo.twilio.com/docs/voice.xml",
            to=address,
            from_=my_number,
        )
