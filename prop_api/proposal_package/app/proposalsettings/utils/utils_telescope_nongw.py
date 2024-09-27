import datetime as dt
import logging
import random
from datetime import datetime

json_logger = logging.getLogger("django_json")


def handle_non_gw_observation(telescope_settings, context):
    """Handle the logic for non-GW observations."""
    if context["stop_processing"]:
        return context

    if context["proposal_decision_model"].proposal.source_type != "GW":
        print("DEBUG - Not a GW so ignoring GW logic")

        json_logger.info(
            f"Handle the logic for non-GW observations",
            extra={
                "function": "handle_non_gw_observation",
                "trig_id": context["proposal_decision_model"].trig_id,
                "event_id": context["event_id"],
                "proposal_id": context["proposal_decision_model"].proposal.id,
            },
        )
        
        (
            context["decision"],
            context["decision_reason_log_obs"],
            context["obsids"],
            context["result"],
        ) = telescope_settings.trigger_telescope(context)

        print(f"result: {context['result']}")
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

            # TODO: ask if we should stop triggering the subsequent events
            # context["stop_processing"] = True

    return context
