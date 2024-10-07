import datetime as dt
import logging
import random
from datetime import datetime

from .utils_log import log_event


@log_event(log_location="end",message=f"Handle the logic for non-GW observations completed", level="info")
def handle_non_gw_observation(telescope_settings, context):
    """Handle the logic for non-GW observations."""
    
    if context["stop_processing"]:
        return context
    
    if context["prop_dec"].proposal.source_type == "GW":
        return context

    # if context["prop_dec"].proposal.source_type != "GW":
    print("DEBUG - Not a GW so ignoring GW logic")
    
    (
        context["decision"],
        context["decision_reason_log_obs"],
        context["obsids"],
        context["result"],
    ) = telescope_settings.trigger_telescope(context)

    # print(f"result: {context['result']}")
    context[
        "decision_reason_log"
    ] += f"{datetime.now(dt.timezone.utc)}: Event ID {context['event_id']}: Saving observation result.\n"
    context["request_sent_at"] = datetime.now(dt.timezone.utc)

    if context["decision"].find("T") > -1:
        saved_obs = telescope_settings.save_observation(
            context,
            trigger_id=context["result"]["trigger_id"]
            or random.randrange(10000, 99999),
            obsid=context["obsids"][0],
            reason=context["reason"],
        )

    context["reached_end"] = True

    return context
