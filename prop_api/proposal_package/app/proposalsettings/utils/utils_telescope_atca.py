import datetime as dt
import logging
from datetime import datetime

json_logger = logging.getLogger("django_json")


def handle_atca_observation(telescope_settings, context):
    """Handle the logic for ATCA observations."""
    if context["stop_processing"]:
        return context

    if telescope_settings.telescope.name != "ATCA":
        return context

    json_logger.info(
        "handle_atca_observation",
        extra={
            "function": "handle_atca_observation",
            "trig_id": context["proposal_decision_model"].trig_id,
            "event_id": context["event_id"],
        },
    )

    if telescope_settings.telescope.name == "ATCA":

        obsname = f"{context['proposal_decision_model'].trig_id}"

        (context["decision"], context["decision_reason_log"], context["obsids"]) = (
            telescope_settings.trigger_telescope(context)
        )

        print("DEBUG - saving ATCA observations")
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

    return context
