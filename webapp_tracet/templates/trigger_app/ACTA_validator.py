from django.core.exceptions import ValidationError
from django import forms
from django.utils.translation import gettext

import logging
import astropy.units as u
from astropy.coordinates import SkyCoord, EarthLocation
from astropy.time import Time
from trigger_app.models import ATCAUser

from tracet.triggerservice import trigger
import atca_rapid_response_api as arrApi

logger = logging.getLogger(__name__)

def atca_proposal_id(project_id, secure_key, atca_email):
    """Check that the ATCA project ID and secure key are valid.

    Parameters
    ----------
    project_id : `str`
        The project ID, e.g. T001.
    secure_key : `str`
        The secure key (password) for this project.
    atca_email : `str`
        The email address of someone that was on the ATCA observing proposal. This is an authentication step.
    """
    # Setup current RA and Dec at zenith for ATCA
    atca = EarthLocation(lat='-30:18:46', lon='149:33:01', height=377.8 * u.m)
    atca_coord = coord = SkyCoord(az=0., alt=90., unit=(u.deg, u.deg), frame='altaz', obstime=Time.now(), location=atca)
    ra = atca_coord.icrs.ra.to_string(unit=u.hour, sep=':')[:11]
    rq = {
        "source": "Test",
        "rightAscension": ra,
        "declination": "-30:18:46",
        "project": project_id,
        "maxExposureLength": "00:01:00",
        "minExposureLength": "00:00:01",
        "scanType": "Dwell",
        "4cm": {
            "use": True,
            "exposureLength": "00:00:20",
            "freq1": 5500,
            "freq2": 9000,
        },
    }

    # We have our request now, so we need to craft the service request to submit it to
    # the rapid response service.
    rapidObj = { 'requestDict': rq }
    rapidObj["authenticationToken"] = secure_key
    rapidObj["email"] = atca_email
    rapidObj["test"] = True
    rapidObj["noTimeLimit"] = True
    rapidObj["noScoreLimit"] = True

    user = ATCAUser.objects.all().first()

    rapidObj['httpAuthUsername'] = user.httpAuthUsername
    rapidObj['httpAuthPassword'] = user.httpAuthPassword

    request = arrApi.api(rapidObj)
    try:
        result = request.send()
    except arrApi.responseError as r:
        logger.error(f"ATCA return message: {r}")
        raise forms.ValidationError({r})

    # Check if succesful
    if result is None:
        raise forms.ValidationError({"Web API error, possible server error"})