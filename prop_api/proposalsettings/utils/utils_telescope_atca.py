import datetime as dt
import logging
from datetime import datetime

from .utils_log import log_event


@log_event(log_location="end",message=f"Handle the logic for ATCA observations completed", level="info")
def handle_atca_observation(telescope_settings, context):
    """Handle the logic for ATCA observations."""
    print("DEBUG - KEYS-handle_atca_observation:", context.keys())
    
    if context["stop_processing"]:
        return context

    if telescope_settings.telescope.name != "ATCA":
        return context

    # if telescope_settings.telescope.name == "ATCA":

    obsname = f"{context['prop_dec'].trig_id}"

    (context["decision"], context["decision_reason_log"], context["obsids"]) = (
        telescope_settings.trigger_telescope(context)
    )

    for obsid in context["obsids"]:
        saved_atca_obs = telescope_settings.save_observation(
            context,
            trigger_id=obsid,
            # TODO see if ATCA has a nice observation details webpage
            # website_link=f"http://ws.mwatelescope.org/observation/obs/?obsid={obsid}",
        )

        context[
            "decision_reason_log"
        ] += f"{datetime.now(dt.timezone.utc)}: Event ID {context['event_id']}: Saving observation result for ATCA.\n"
        context["request_sent_at"] = datetime.now(dt.timezone.utc)
        
    context["reached_end"] = True

    return context
