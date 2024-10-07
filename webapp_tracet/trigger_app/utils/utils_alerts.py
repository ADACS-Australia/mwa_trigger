import logging
import os

import numpy as np
from astropy import units as u
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.time import Time
from django.conf import settings
from django.core.mail import send_mail
from trigger_app.models.alert import AlertPermission, UserAlerts
from trigger_app.models.event import Event
from trigger_app.models.observation import Observations
from twilio.rest import Client

logger = logging.getLogger(__name__)

account_sid = os.environ.get("TWILIO_ACCOUNT_SID", None)
auth_token = os.environ.get("TWILIO_AUTH_TOKEN", None)
my_number = os.environ.get("TWILIO_PHONE_NUMBER", None)


def send_all_alerts(trigger_bool, debug_bool, pending_bool, prop_dec):
    """ """
    # Work out all the telescopes that observed the event
    logger.info(
        f"Work out all the telescopes that observed the event {trigger_bool, debug_bool, pending_bool, prop_dec}"
    )
    voevents = Event.objects.filter(
        event_group_id=prop_dec.event_group_id
    )

    # print(f"\nDEBUG - send email - checking events\n")

    telescopes = []
    for voevent in voevents:
        telescopes.append(voevent.telescope)
    # Make sure they are unique and put each on a new line
    telescopes = ", ".join(list(set(telescopes)))

    # Work out when the source will go below the horizon
    telescope = prop_dec.proposal.telescope
    location = EarthLocation(
        lon=telescope.lon * u.deg,
        lat=telescope.lat * u.deg,
        height=telescope.height * u.m,
    )

    # print(f"\nDEBUG - send email - checking telescope location\n")

    if prop_dec.ra and prop_dec.dec:
        obs_source = SkyCoord(
            prop_dec.ra,
            prop_dec.dec,
            # equinox='J2000',
            unit=(u.deg, u.deg),
        )
        # print(f"\nDEBUG - send email - obs_source calculated \n")
        # Convert from RA/Dec to Alt/Az
        # 24 hours in 5 min increments
        delta_24h = np.linspace(0, 1440, 288) * u.min
        next_24h = obstime = Time.now() + delta_24h

        # print(f"\nDEBUG - send email - obstime calculated\n")

        obs_source_altaz = obs_source.transform_to(
            AltAz(obstime=next_24h, location=location)
        )

        # print(f"\nDEBUG - send email - obs_source_altaz calculated\n")

        # capture circumpolar source case
        set_time_utc = None
        for altaz, time in zip(obs_source_altaz, next_24h):
            if altaz.alt.deg < 1.0:
                # source below horizon so record time
                set_time_utc = time
                break

    # Get all admin alert permissions for this project
    logger.info("Get all admin alert permissions for this project")

    # print(f"\nDEBUG - send email - Get all admin alert permissions for this project\n")

    alert_permissions = AlertPermission.objects.filter(
        proposal=prop_dec.proposal
    )
    for ap in alert_permissions:
        # Grab user
        user = ap.user
        user_alerts = UserAlerts.objects.filter(
            user=user, proposal=prop_dec.proposal
        )

        # Send off the alerts of types user defined
        for ua in user_alerts:
            # Check if user can recieve each type of alert
            # Trigger alert
            if ap.alert and ua.alert and trigger_bool:
                subject = f"TraceT {prop_dec.proposal.proposal_id}: {prop_dec.proposal.telescope_id} TRIGGERING on {telescopes} {prop_dec.event_group_id.source_type}"
                message_type_text = f"Tracet scheduled the following {prop_dec.proposal.telescope} observations:\n"
                # Send links for each observation
                obs = Observations.objects.filter(
                    proposal_decision_id=prop_dec
                )
                for ob in obs:
                    message_type_text += f"{ob.website_link}\n"
                try:
                    send_alert_type(
                        ua.type,
                        ua.address,
                        subject,
                        message_type_text,
                        prop_dec,
                        telescopes,
                        set_time_utc,
                    )
                except Exception as e:
                    logger.error(f"Twillio error message: {e}")

            # Debug Alert
            if ap.debug and ua.debug and debug_bool:
                subject = f"TraceT {prop_dec.proposal.proposal_id}: {prop_dec.proposal.telescope_id} INFO on {telescopes} {prop_dec.event_group_id.source_type}"
                message_type_text = f"This is a debug notification from TraceT."
                try:
                    send_alert_type(
                        ua.type,
                        ua.address,
                        subject,
                        message_type_text,
                        prop_dec,
                        telescopes,
                        set_time_utc,
                    )
                except Exception as e:
                    logger.error(f"Twillio error message: {e}")

            # Pending Alert
            if ap.approval and ua.approval and pending_bool:
                subject = f"TraceT {prop_dec.proposal.proposal_id}: {prop_dec.proposal.telescope_id} PENDING on {telescopes} {prop_dec.event_group_id.source_type}"
                message_type_text = f"HUMAN INTERVENTION REQUIRED! TraceT is unsure about the following event."
                try:
                    send_alert_type(
                        ua.type,
                        ua.address,
                        subject,
                        message_type_text,
                        prop_dec,
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
    prop_dec,
    telescopes,
    set_time_utc,
):
    # Set up twillo client for SMS and calls
    client = Client(account_sid, auth_token)

    # Set up message text
    message_text = f"""{message_type_text}

Event Details are:
TraceT proposal:      {prop_dec.proposal.proposal_id}
Detected by: {telescopes}
Event Type:  {prop_dec.event_group_id.source_type}
Duration:    {prop_dec.duration}
RA:          {prop_dec.ra_hms} hours
Dec:         {prop_dec.dec_dms} deg
Error Rad:   {prop_dec.pos_error} deg
Event observed (UTC): {prop_dec.event_group_id.earliest_event_observed}
Set time (UTC):       {set_time_utc}

Decision log:
{prop_dec.decision_reason}

Proposal decision can be seen here:
https://mwa-trigger.duckdns.org/proposal_decision_details/{prop_dec.id}/
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
