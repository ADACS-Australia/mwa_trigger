import logging
from datetime import datetime
from datetime import timezone as dt

import atca_rapid_response_api as arrApi
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse

from .. import models

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.level = logging.INFO

@login_required
def MWAResponse(request, id):
    observation = models.observation.Observations.objects.get(trigger_id=id)
    if observation.mwa_response:
        return JsonResponse(observation.mwa_response, safe=False)
    else:
        # Return a 404 if the data is not found
        return JsonResponse({"error": "Data not found"}, status=404)
    
    


@login_required
def cancel_atca_observation(request, id=None):
    # Grab obs and proposal data
    obs = models.observation.Observations.objects.filter(trigger_id=id).first()
    proposal_settings = obs.proposal_decision_id.proposal
    decision_reason_log = obs.proposal_decision_id.decision_reason

    # Create the cancel request
    rapidObj = {
        "requestDict": {
            "cancel": obs.trigger_id,
            "project": proposal_settings.project_id.id,
        }
    }
    rapidObj["authenticationToken"] = proposal_settings.project_id.password
    rapidObj["email"] = proposal_settings.project_id.atca_email

    user = models.user.ATCAUser.objects.all().first()

    rapidObj["httpAuthUsername"] = user.httpAuthUsername
    rapidObj["httpAuthPassword"] = user.httpAuthPassword

    # Send the request.
    atca_request = arrApi.api(rapidObj)
    try:
        response = atca_request.send()
    except arrApi.responseError as r:
        logger.error(f"ATCA return message: {r}")
        decision_reason_log += f"ATCA cancel failed, return message: {r}\n "
        decision = "E"
    else:
        decision_reason_log += (
            f"ATCA observation canceled at {datetime.now(dt.timezone.utc)}. \n"
        )
        decision = "C"
    # Update propocal decision
    prop_dec = obs.proposal_decision_id
    prop_dec.decision_reason = decision_reason_log
    prop_dec.decision = decision
    prop_dec.save()

    return HttpResponseRedirect(request.META.get("HTTP_REFERER"))
