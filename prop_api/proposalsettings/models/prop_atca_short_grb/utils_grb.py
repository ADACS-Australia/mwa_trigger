import datetime as dt
import logging
from datetime import datetime
from functools import partial
from typing import Tuple, Union

from ...utils.utils_log import log_event, log_event_with_error
from ..event import Event
from ..telescopesettings import BaseTelescopeSettings

logger = logging.getLogger(__name__)


def initialize_context(event: Event, kwargs: dict) -> dict:
    """
    Initialize the context dictionary with event information and default values.

    Args:
        event (Event): The GRB event to evaluate.
        kwargs (dict): Additional keyword arguments.

    Returns:
        dict: The initialized context dictionary.
    """
    prop_dec = kwargs.get("prop_dec")

    return {
        "event": event,
        "event_id": event.id,
        "dec": kwargs.get("dec"),
        "decision_reason_log": kwargs.get("decision_reason_log", ""),
        "trigger_bool": False,
        "debug_bool": False,
        "pending_bool": False,
        "likely_bool": False,
        "stop_processing": False,
        "trig_id": prop_dec.trig_id,
        "prop_dec": prop_dec,
    }


@log_event(message=f"Position uncertainty is 0.0, not observing.", level="debug")
def check_position_error(context: dict) -> dict:
    """
    Check if the event's position uncertainty is 0.0.

    If the position uncertainty is 0.0, mark the event as not worth observing.

    Args:
        context (dict): The context dictionary containing event information.

    Returns:
        dict: The updated context dictionary.
    """
    event = context["event"]
    dec = context["dec"]

    if event.pos_error is None:
        return context

    if event.pos_error != 0.0:
        return context

    # if event.pos_error == 0.0:

    # Ignore the inaccurate event
    context["debug_bool"] = True
    context["stop_processing"] = True
    context["decision_reason_log"] += (
        f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: The event's position uncertainty is 0.0, "
        "which is likely an error, so not observing. \n"
    )

    context['reached_end'] = True

    return context


@log_event(
    log_location="end",
    message=f"Position uncertainty is large, not observing.",
    level="debug",
)
def check_large_position_error(
    telescope_settings: BaseTelescopeSettings, context: dict
) -> dict:
    """
    Check if the event's position uncertainty is larger than the maximum allowed.

    If the position uncertainty is too large, mark the event as not worth observing.

    Args:
        telescope_settings (BaseTelescopeSettings): The telescope settings.
        context (dict): The context dictionary containing event information.

    Returns:
        dict: The updated context dictionary.
    """
    if context["stop_processing"]:
        return context

    event = context["event"]

    if event.pos_error is None:
        return context

    if (
        telescope_settings.maximum_position_uncertainty
        and event.pos_error > telescope_settings.maximum_position_uncertainty
    ) is False:
        return context

    # if (
    #     telescope_settings.maximum_position_uncertainty
    #     and event.pos_error > telescope_settings.maximum_position_uncertainty
    # ):
    # Ignore the inaccurate event
    context["debug_bool"] = True
    context["stop_processing"] = True
    context["decision_reason_log"] += (
        f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: The event's position uncertainty ({event.pos_error:.4f} deg) "
        f"is greater than {telescope_settings.maximum_position_uncertainty:.4f} so not observing. \n"
    )

    context['reached_end'] = True

    return context


@log_event(message=f"Declination is outside ATCA limits, not observing.", level="debug")
def check_atca_declination_limits(
    telescope_settings: BaseTelescopeSettings, context: dict
) -> dict:
    """
    Check if the event's declination is within the ATCA telescope limits.

    If the declination is outside the limits, mark the event as not worth observing.

    Args:
        telescope_settings (BaseTelescopeSettings): The telescope settings.
        context (dict): The context dictionary containing event information.

    Returns:
        dict: The updated context dictionary.
    """
    if context["stop_processing"]:
        return context

    if telescope_settings.telescope.name != "ATCA":
        return context

    dec = context["dec"]

    if (
        telescope_settings.atca_dec_min_1 < dec < telescope_settings.atca_dec_max_1
    ) or (telescope_settings.atca_dec_min_2 < dec < telescope_settings.atca_dec_max_2):
        return context

    # Ignore the inaccurate event
    context["debug_bool"] = True
    context["stop_processing"] = True
    context["decision_reason_log"] += (
        f"{datetime.now(dt.timezone.utc)}: Event ID {context['event'].id}: The event's declination ({dec}) is outside "
        f"limit 1 ({telescope_settings.atca_dec_min_1} < dec < {telescope_settings.atca_dec_max_1}) or limit 2 ({telescope_settings.atca_dec_min_2} < dec < {telescope_settings.atca_dec_max_2}). \n"
    )

    context['reached_end'] = True

    return context


# Check Fermi most likely index and detection probability
@log_event(message=f"Fermi GRB probability checked", level="debug")
def check_fermi_likelihood(
    telescope_settings: BaseTelescopeSettings, context: dict
) -> dict:
    """
    Check the Fermi GRB probability and most likely index.

    Determine if the event is likely to be a GRB based on Fermi data.

    Args:
        telescope_settings (BaseTelescopeSettings): The telescope settings.
        context (dict): The context dictionary containing event information.

    Returns:
        dict: The updated context dictionary.
    """
    if context["stop_processing"]:
        return context

    event = context["event"]

    if event.fermi_most_likely_index is None:
        return context

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

    context["stop_processing"] = True
    context['reached_end'] = True

    return context


# Check Swift rate significance
@log_event(message=f"Swift rate significance checked", level="debug")
def check_swift_significance(
    telescope_settings: BaseTelescopeSettings, context: dict
) -> dict:
    """
    Check the Swift rate significance.

    Determine if the event is likely to be a GRB based on Swift data.

    Args:
        telescope_settings (BaseTelescopeSettings): The telescope settings.
        context (dict): The context dictionary containing event information.

    Returns:
        dict: The updated context dictionary.
    """
    if context["stop_processing"]:
        return context

    event = context["event"]
    if event.swift_rate_signif is None:
        return context

    # if event.swift_rate_signif is not None:
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

    context["stop_processing"] = True

    context['reached_end'] = True

    return context


# Check HESS significance
@log_event(message=f"HESS significance checked", level="debug")
def check_hess_significance(
    telescope_settings: BaseTelescopeSettings, context: dict
) -> dict:
    """
    Check the HESS significance.

    Determine if the event is likely to be a GRB based on HESS data.

    Args:
        telescope_settings (BaseTelescopeSettings): The telescope settings.
        context (dict): The context dictionary containing event information.

    Returns:
        dict: The updated context dictionary.
    """
    if context["stop_processing"]:
        return context

    event = context["event"]

    if event.hess_significance is None:
        return context

    # if event.hess_significance is not None:
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

    context["stop_processing"] = True
    context['reached_end'] = True
    return context


# Default if no likelihood data is available
@log_event(
    message=f"Assuming it is a GRB if no likelihood data is available", level="debug"
)
def default_no_likelihood(context: dict) -> dict:
    """
    Set the event as likely to be a GRB if no likelihood data is available.

    Args:
        context (dict): The context dictionary containing event information.

    Returns:
        dict: The updated context dictionary.
    """
    if context["stop_processing"]:
        return context

    context["likely_bool"] = True
    context[
        "decision_reason_log"
    ] += f"{datetime.now(dt.timezone.utc)}: Event ID {context['event'].id}: No probability metric given so assume it is a GRB. \n"

    context["stop_processing"] = True
    context['reached_end'] = True
    return context


# new if block starts and stop_processing is False
@log_event(message=f"Accepting any event duration, triggering.", level="debug")
def check_any_event_duration(
    telescope_settings: BaseTelescopeSettings, context: dict
) -> dict:
    """
    Check if the telescope settings allow for any event duration.

    If so, mark the event for triggering an observation.

    Args:
        telescope_settings (BaseTelescopeSettings): The telescope settings.
        context (dict): The context dictionary containing event information.

    Returns:
        dict: The updated context dictionary.
    """
    if context["stop_processing"]:
        return context

    event = context["event"]

    if (
        telescope_settings.event_any_duration
        and context["likely_bool"]
        and not context["debug_bool"]
    ) is False:
        return context

    context["stop_processing"] = True
    context["trigger_bool"] = True
    context[
        "decision_reason_log"
    ] += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: Accepting any event duration so triggering. \n"

    context['reached_end'] = True
    return context


@log_event(message=f"No event duration, not triggering.", level="debug")
def check_not_any_event_duration(
    telescope_settings: BaseTelescopeSettings, context: dict
) -> dict:
    """
    Check if the event has no duration and the telescope doesn't accept any duration.

    If so, mark the event as not worth observing.

    Args:
        telescope_settings (BaseTelescopeSettings): The telescope settings.
        context (dict): The context dictionary containing event information.

    Returns:
        dict: The updated context dictionary.
    """
    if context["stop_processing"]:
        return context

    event = context["event"]

    if (
        not telescope_settings.event_any_duration
        and event.duration is None
        and not context["debug_bool"]
    ) is False:
        return context

    context["stop_processing"] = True
    context["debug_bool"] = True
    context[
        "decision_reason_log"
    ] += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: No event duration (None) so not triggering. \n"

    context['reached_end'] = True
    return context


def check_duration_with_limits(
    telescope_settings: BaseTelescopeSettings, context: dict
) -> dict:
    """
    Check if the event duration is within the specified limits.

    This function calls other functions to check various duration criteria.

    Args:
        telescope_settings (BaseTelescopeSettings): The telescope settings.
        context (dict): The context dictionary containing event information.

    Returns:
        dict: The updated context dictionary.
    """
    if context["stop_processing"]:
        return context

    # event.duration is not None and likely_bool and not debug_bool
    event = context["event"]

    if (
        event.duration is not None
        and context["likely_bool"]
        and not context["debug_bool"]
    ) is False:
        return context

    context = check_duration_with_limits_trigger(telescope_settings, context)

    context = check_duration_with_limits_pending1(telescope_settings, context)

    context = check_duration_with_limits_pending2(telescope_settings, context)

    context = check_duration_with_limits_debug(telescope_settings, context)

    return context


@log_event(message=f"Event duration within limits, triggering.", level="debug")
def check_duration_with_limits_trigger(
    telescope_settings: BaseTelescopeSettings, context: dict
) -> dict:

    event = context["event"]

    if (
        telescope_settings.event_min_duration
        <= event.duration
        <= telescope_settings.event_max_duration
    ) is False:
        return context

    context["trigger_bool"] = True
    context[
        "decision_reason_log"
    ] += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: Event duration between {telescope_settings.event_min_duration} and {telescope_settings.event_max_duration} s so triggering. \n"

    context["stop_processing"] = True

    context['reached_end'] = True

    return context


@log_event(
    message=f"Event duration within limits 1, waiting for a human's decision.",
    level="debug",
)
def check_duration_with_limits_pending1(
    telescope_settings: BaseTelescopeSettings, context: dict
) -> dict:

    if context["stop_processing"]:
        return context

    event = context["event"]

    if (
        telescope_settings.pending_min_duration_1
        <= event.duration
        <= telescope_settings.pending_max_duration_1
    ) is False:
        return context

    context["pending_bool"] = True
    context[
        "decision_reason_log"
    ] += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: Event duration between {telescope_settings.pending_min_duration_1} and {telescope_settings.pending_max_duration_1} s so waiting for a human's decision. \n"

    context["stop_processing"] = True

    context['reached_end'] = True

    return context


@log_event(
    message=f"Event duration within limits 2, waiting for a human's decision.",
    level="debug",
)
def check_duration_with_limits_pending2(
    telescope_settings: BaseTelescopeSettings, context: dict
) -> dict:

    if context["stop_processing"]:
        return context

    event = context["event"]

    if (
        telescope_settings.pending_min_duration_2
        <= event.duration
        <= telescope_settings.pending_max_duration_2
    ) is False:
        return context

    context["pending_bool"] = True
    context[
        "decision_reason_log"
    ] += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: Event duration between {telescope_settings.pending_min_duration_2} and {telescope_settings.pending_max_duration_2} s so waiting for a human's decision. \n"

    context["stop_processing"] = True

    context['reached_end'] = True

    return context


@log_event(
    message=f"Event duration outside of all time ranges, not triggering.", level="debug"
)
def check_duration_with_limits_debug(
    telescope_settings: BaseTelescopeSettings, context: dict
) -> dict:
    if context["stop_processing"]:
        return context

    event = context["event"]

    context["debug_bool"] = True
    context[
        "decision_reason_log"
    ] += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: Event duration outside of all time ranges so not triggering. \n"

    context["stop_processing"] = True

    context['reached_end'] = True

    return context
