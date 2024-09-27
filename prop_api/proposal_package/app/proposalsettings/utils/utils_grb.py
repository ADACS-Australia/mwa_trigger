import datetime as dt
import logging
from datetime import datetime
from functools import partial
from typing import Tuple, Union

logger = logging.getLogger(__name__)

json_logger = logging.getLogger("django_json")


# Initialize the context with the event and defaults
def initialize_context(event, kwargs) -> dict:
    return {
        "event": event,
        "dec": kwargs.get("dec"),
        "decision_reason_log": kwargs.get("decision_reason_log", ""),
        "trigger_bool": False,
        "debug_bool": False,
        "pending_bool": False,
        "likely_bool": False,
        "stop_processing": False,
    }


def check_position_error(telescope_settings, context) -> dict:
    event = context["event"]
    dec = context["dec"]
    if event.pos_error == 0.0:
        # Ignore the inaccurate event
        context["debug_bool"] = True
        context["stop_processing"] = True
        context["decision_reason_log"] += (
            f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: The event's position uncertainty is 0.0, "
            "which is likely an error, so not observing. \n"
        )

    return context


def check_large_position_error(telescope_settings, context) -> dict:
    if context["stop_processing"]:
        return context

    event = context["event"]
    if (
        telescope_settings.maximum_position_uncertainty
        and event.pos_error > telescope_settings.maximum_position_uncertainty
    ):
        # Ignore the inaccurate event
        context["debug_bool"] = True
        context["stop_processing"] = True
        context["decision_reason_log"] += (
            f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: The event's position uncertainty ({event.pos_error:.4f} deg) "
            f"is greater than {telescope_settings.maximum_position_uncertainty:.4f} so not observing. \n"
        )
    return context


def check_atca_declination_limits(telescope_settings, context) -> dict:
    if context["stop_processing"]:
        return context

    if telescope_settings.telescope.name == "ATCA":
        dec = context["dec"]
        if not (
            (
                telescope_settings.atca_dec_min_1
                < dec
                < telescope_settings.atca_dec_max_1
            )
            or (
                telescope_settings.atca_dec_min_2
                < dec
                < telescope_settings.atca_dec_max_2
            )
        ):
            # Ignore the inaccurate event
            context["debug_bool"] = True
            context["stop_processing"] = True
            context["decision_reason_log"] += (
                f"{datetime.now(dt.timezone.utc)}: Event ID {context['event'].id}: The event's declination ({dec}) is outside "
                f"limit 1 ({telescope_settings.atca_dec_min_1} < dec < {telescope_settings.atca_dec_max_1}) or limit 2 ({telescope_settings.atca_dec_min_2} < dec < {telescope_settings.atca_dec_max_2}). \n"
            )

    return context


# Check Fermi most likely index and detection probability
def check_fermi_likelihood(telescope_settings, context) -> dict:
    if context["stop_processing"]:
        return context

    event = context["event"]
    if event.fermi_most_likely_index is not None:
        context["stop_processing"] = True
        # Fermi triggers have their own probability
        if event.fermi_most_likely_index == 4:
            logger.debug("MOST_LIKELY = GRB")
            print("DEBUG - MOST_LIKELY = GRB")
            if event.fermi_detection_prob >= telescope_settings.fermi_prob:
                context["likely_bool"] = True
                context[
                    "decision_reason_log"
                ] += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: Fermi GRB probability greater than {telescope_settings.fermi_prob}. \n"
            else:
                context["debug_bool"] = True
                context[
                    "decision_reason_log"
                ] += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: Fermi GRB probability less than {telescope_settings.fermi_prob} so not triggering. \n"
        else:
            context["debug_bool"] = True
            context[
                "decision_reason_log"
            ] += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: Fermi GRB likely index not 4. \n"
    return context


# Check Swift rate significance
def check_swift_significance(telescope_settings, context) -> dict:
    if context["stop_processing"]:
        return context

    event = context["event"]
    if event.swift_rate_signif is not None:
        context["stop_processing"] = True

        if event.swift_rate_signif >= telescope_settings.swift_rate_signif:
            context["likely_bool"] = True
            context[
                "decision_reason_log"
            ] += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: SWIFT rate significance ({event.swift_rate_signif}) >= swift_min_rate ({telescope_settings.swift_rate_signif:.3f}) sigma. \n"
        else:
            context["debug_bool"] = True
            context[
                "decision_reason_log"
            ] += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: SWIFT rate significance ({event.swift_rate_signif}) < swift_min_rate ({telescope_settings.swift_rate_signif:.3f}) sigma so not triggering. \n"
    return context


# Check HESS significance
def check_hess_significance(telescope_settings, context) -> dict:
    if context["stop_processing"]:
        return context

    event = context["event"]
    if event.hess_significance is not None:
        context["stop_processing"] = True
        if (
            telescope_settings.minimum_hess_significance
            <= event.hess_significance
            <= telescope_settings.maximum_hess_significance
        ):
            context["likely_bool"] = True
            context["decision_reason_log"] += (
                f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: HESS rate significance is "
                f"{telescope_settings.minimum_hess_significance} <= ({event.hess_significance:.3f}) <= {telescope_settings.maximum_hess_significance} sigma. \n"
            )
        else:
            context["debug_bool"] = True
            context["decision_reason_log"] += (
                f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: HESS rate significance is not "
                f"{telescope_settings.minimum_hess_significance} <= ({event.hess_significance:.3f}) <= {telescope_settings.maximum_hess_significance} so not triggering. \n"
            )
    return context


# Default if no likelihood data is available
def default_no_likelihood(context) -> dict:
    if context["stop_processing"]:
        return context

    context["likely_bool"] = True
    context[
        "decision_reason_log"
    ] += f"{datetime.now(dt.timezone.utc)}: Event ID {context['event'].id}: No probability metric given so assume it is a GRB. \n"

    return context


# new if starts


def check_any_event_duration(telescope_settings, context) -> dict:
    if context["stop_processing"]:
        return context

    event = context["event"]
    if (
        telescope_settings.event_any_duration
        and context["likely_bool"]
        and not context["debug_bool"]
    ):
        context["stop_processing"] = True
        context["trigger_bool"] = True
        context[
            "decision_reason_log"
        ] += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: Accepting any event duration so triggering. \n"

    return context


def check_not_any_event_duration(telescope_settings, context) -> dict:
    if context["stop_processing"]:
        return context

    event = context["event"]
    if (
        not telescope_settings.event_any_duration
        and event.duration is None
        and not context["debug_bool"]
    ):
        context["stop_processing"] = True
        context["debug_bool"] = True
        context[
            "decision_reason_log"
        ] += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: No event duration (None) so not triggering. \n"

    return context


def check_duration_with_limits(telescope_settings, context) -> dict:
    if context["stop_processing"]:
        return context

    # event.duration is not None and likely_bool and not debug_bool
    event = context["event"]
    if (
        event.duration is not None
        and context["likely_bool"]
        and not context["debug_bool"]
    ):
        context["stop_processing"] = True
        if (
            telescope_settings.event_min_duration
            <= event.duration
            <= telescope_settings.event_max_duration
        ):
            context["trigger_bool"] = True
            context[
                "decision_reason_log"
            ] += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: Event duration between {telescope_settings.event_min_duration} and {telescope_settings.event_max_duration} s so triggering. \n"
        elif (
            telescope_settings.pending_min_duration_1
            <= event.duration
            <= telescope_settings.pending_max_duration_1
        ):
            context["pending_bool"] = True
            context[
                "decision_reason_log"
            ] += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: Event duration between {telescope_settings.pending_min_duration_1} and {telescope_settings.pending_max_duration_1} s so waiting for a human's decision. \n"
        elif (
            telescope_settings.pending_min_duration_2
            <= event.duration
            <= telescope_settings.pending_max_duration_2
        ):
            context["pending_bool"] = True
            context[
                "decision_reason_log"
            ] += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: Event duration between {telescope_settings.pending_min_duration_2} and {telescope_settings.pending_max_duration_2} s so waiting for a human's decision. \n"
        else:
            context["debug_bool"] = True
            context[
                "decision_reason_log"
            ] += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: Event duration outside of all time ranges so not triggering. \n"

    return context
