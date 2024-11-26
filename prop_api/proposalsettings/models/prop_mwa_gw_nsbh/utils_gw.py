import datetime as dt
import logging
from datetime import datetime, timedelta
from functools import partial
from typing import Tuple, Union

from ...utils.utils_log import log_event, log_event_with_error
from ..event import Event

# Initialize the context with the event and defaults


def initialize_context(event: Event, kwargs: dict) -> dict:
    """
    Initialize the context dictionary with event information and default values.

    This function sets up the initial context that will be passed through all subsequent
    functions in the gravitational wave observation decision process.

    Args:
        event (Event): The gravitational wave event to be processed.
        kwargs (Dict[str, Any]): Additional keyword arguments.

    Returns:
        Dict[str, Any]: The initialized context dictionary.
    """

    prop_dec = kwargs.get("prop_dec")

    context = {
        "event_id": event.id,
        "event": event,
        "decision_reason_log": kwargs.get("decision_reason_log", ""),
        "trigger_bool": False,
        "debug_bool": False,  # This remains for its original purpose
        "pending_bool": False,
        "FAR": None,
        "FARThreshold": None,
        "stop_processing": False,  # New flag to control short-circuiting
        "trig_id": prop_dec.trig_id,
        "prop_dec": prop_dec,
    }

    return context


# Process the False Alarm Rate (FAR)
@log_event_with_error(
    message="Processing FAR values", level="debug", handle_errors=True
)
def process_false_alarm_rate(context: dict, maximum_false_alarm_rate: float) -> dict:
    """
    Process the False Alarm Rate (FAR) for the event.

    This function compares the event's FAR with the maximum allowed FAR and updates
    the context accordingly. It's typically one of the first checks in the decision process.

    Args:
        context (Dict[str, Any]): The context dictionary containing event information.
        maximum_false_alarm_rate (float): The maximum allowed false alarm rate.

    Returns:
        Dict[str, Any]: The updated context dictionary.
    """
    event = context["event"]

    if event.lvc_false_alarm_rate is None:
        return context

    if maximum_false_alarm_rate is None:
        return context

    # if event.lvc_false_alarm_rate and maximum_false_alarm_rate:
    try:
        # maximum_false_alarm_rate = 1/'a'
        context["FAR"] = float(event.lvc_false_alarm_rate)
        context["FARThreshold"] = float(maximum_false_alarm_rate)

        context['reached_end'] = True

    except Exception as e:
        context["debug_bool"] = True
        context["stop_processing"] = True
        context["decision_reason_log"] += (
            f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: The event FAR ({event.lvc_false_alarm_rate}) "
            f"or proposal FAR ({maximum_false_alarm_rate}) could not be processed so not triggering. \n"
        )
        raise  # Re-raise the exception to be caught by the decorator

    return context


@log_event(message="Early warning detected. Triggering.", level="info")
def update_event_parameters(context: dict) -> dict:
    """
    Update event parameters for early warning LVC events.

    This function checks if the event is an LVC early warning and updates probabilities
    accordingly. Early warning events are always triggered for observation.

    Args:
        context (Dict[str, Any]): The context dictionary containing event information.

    Returns:
        Dict[str, Any]: The updated context dictionary.
    """
    event = context["event"]

    if event.telescope != "LVC":
        return context

    if event.event_type != "EarlyWarning":
        return context

    # if event.telescope == "LVC" and event.event_type == "EarlyWarning":

    context["trigger_bool"] = True  # Always trigger on Early Warning events
    event.lvc_binary_neutron_star_probability = 0.97
    event.lvc_neutron_star_black_hole_probability = 0.01
    event.lvc_binary_black_hole_probability = 0.01
    event.lvc_terrestial_probability = 0.01

    context["event"] = event

    context['reached_end'] = True

    return context


# Check event time against a threshold of 2 hours ago
@log_event(message="Event more than 2 hours ago. Not observing.", level="debug")
def check_event_time(context: dict) -> dict:
    """
    Check if the event occurred within the last 2 hours.

    This function determines if the event is too old to be observed based on a 2-hour threshold.

    Args:
        context (Dict[str, Any]): The context dictionary containing event information.

    Returns:
        Dict[str, Any]: The updated context dictionary.
    """
    event = context["event"]
    two_hours_ago = datetime.now(dt.timezone.utc) - dt.timedelta(hours=2)

    if event.event_observed is None:
        return context

    if event.event_observed >= two_hours_ago:
        return context

    # if event.event_observed < two_hours_ago:

    context["stop_processing"] = True
    context["trigger_bool"] = False
    context["decision_reason_log"] += (
        f'{datetime.now(dt.timezone.utc)}: Event ID {event.id}: The event time {event.event_observed.strftime("%Y-%m-%dT%H:%M:%S+0000")} '
        f'is more than 2 hours ago {two_hours_ago.strftime("%Y-%m-%dT%H:%M:%S+0000")} so not triggering. \n'
    )

    context['reached_end'] = True

    return context


# Check the number of LVC instruments involved
@log_event(message="Event has only one instrument - not triggering", level="debug")
def check_lvc_instruments(context: dict) -> dict:
    """
    Check the number of LVC instruments involved in the event detection.

    This function ensures that at least two instruments were involved in detecting the event.

    Args:
        context (Dict[str, Any]): The context dictionary containing event information.

    Returns:
        Dict[str, Any]: The updated context dictionary.
    """
    # Short-circuit if a previous condition was met
    if context["stop_processing"]:
        return context

    event = context["event"]

    if event.lvc_instruments is None:
        return context

    if len(event.lvc_instruments.split(",")) >= 2:
        return context

    # if event.lvc_instruments and len(event.lvc_instruments.split(",")) < 2:
    context["stop_processing"] = True
    context["debug_bool"] = True
    context[
        "decision_reason_log"
    ] += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: The event has only {event.lvc_instruments} so not triggering. \n"

    context['reached_end'] = True

    return context


# Handle specific event types and telescope
@log_event(message="Event is a retraction. Not observing.", level="debug")
def handle_event_types(context: dict) -> dict:
    """
    Handle specific event types, particularly retractions.

    This function checks if the event is a retraction and updates the context accordingly.

    Args:
        context (Dict[str, Any]): The context dictionary containing event information.

    Returns:
        Dict[str, Any]: The updated context dictionary.
    """
    # Short-circuit if a previous condition was met
    if context["stop_processing"]:
        return context

    event = context["event"]

    if event.telescope != "LVC":
        return context

    if event.event_type != "Retraction":
        return context

    # if event.telescope == "LVC" and event.event_type == "Retraction":
    context["stop_processing"] = True
    context["debug_bool"] = True
    context[
        "decision_reason_log"
    ] += f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: Retraction, scheduling no capture observation (WIP, ignoring for now). \n"

    context['reached_end'] = True

    return context


# Check all probabilities by chaining individual checks with short-circuiting
def check_probabilities(telescope_settings, gw_settings, context: dict) -> dict:
    """
    Check all probabilities related to the gravitational wave event.

    This function serves as a wrapper to call individual probability checks and determine
    if the event is worth observing based on various probability thresholds.

    Args:
        telescope_settings : Settings object related to the telescope.
        gw_settings : Gravitational wave settings object.
        context (Dict[str, Any]): The context dictionary containing event information.

    Returns:
        Dict[str, Any]: The updated context dictionary.
    """
    if context["stop_processing"]:
        return context

    event = context["event"]

    if event.telescope != "LVC":
        return context

    context = check_far_against_threshold(context)
    context = check_ns_probability(gw_settings, context)
    context = check_bns_probability(gw_settings, context)
    context = check_nsb_h_probability(gw_settings, context)
    context = check_bbh_probability(gw_settings, context)
    context = check_terrestrial_probability(gw_settings, context)
    context = check_significance(telescope_settings, context)

    # only this block is triggering
    context = consider_triggering(context)

    return context


@log_event(message="Event is worth observing", level="debug")
def consider_triggering(context: dict) -> dict:
    """
    Determine if the event is worth observing after all checks.

    This function is called if no previous conditions prevented triggering and sets
    the final trigger status.

    Args:
        context (Dict[str, Any]): The context dictionary containing event information.

    Returns:
        Dict[str, Any]: The updated context dictionary with the final trigger decision.
    """

    if context["stop_processing"]:
        return context

    if event.telescope != "LVC":
        return context

    event = context["event"]

    context["trigger_bool"] = True
    context[
        "decision_reason_log"
    ] += f"{datetime.now(dt.timezone.utc)}: Event ID {context['event'].id}: The probability looks good so triggering. \n"

    context['reached_end'] = True

    return context


# Check FAR against the threshold
@log_event(message="FAR is greater than threshold. Not triggering", level="debug")
def check_far_against_threshold(context: dict) -> dict:

    if context["stop_processing"]:
        return context

    if context["FAR"] is None:
        return context

    if context["FARThreshold"] is None:
        return context

    if context["FAR"] <= context["FARThreshold"]:
        return context

    # if context["FAR"] > context["FARThreshold"]:

    context["stop_processing"] = True
    context["debug_bool"] = True
    context["decision_reason_log"] += (
        f"{datetime.now(dt.timezone.utc)}: Event ID {context['event'].id}: The FAR is {context['FAR']} "
        f"which is greater than the threshold {context['FARThreshold']} so not triggering. \n"
    )

    context['reached_end'] = True

    return context


# Check individual probabilities and short-circuit if a condition is met
@log_event(message="NS probability is out of range. Not triggering", level="debug")
def check_ns_probability(gw_settings, context: dict) -> dict:
    """
    Check if the neutron star probability is within the acceptable range.

    This function verifies if the probability of the event involving a neutron star
    is within the defined range in the GW settings.

    Args:
        gw_settings : Gravitational wave settings object.
        context (Dict[str, Any]): The context dictionary containing event information.

    Returns:
        Dict[str, Any]: The updated context dictionary.
    """
    if context["stop_processing"]:
        return context

    if context["event"].lvc_includes_neutron_star_probability is None:
        return context

    event = context["event"]
    # if event.lvc_includes_neutron_star_probability:

    if (
        event.lvc_includes_neutron_star_probability
        <= gw_settings.maximum_neutron_star_probability
    ) and (
        event.lvc_includes_neutron_star_probability
        >= gw_settings.minimum_neutron_star_probability
    ):
        return context

    context["stop_processing"] = True
    context["debug_bool"] = True
    context["decision_reason_log"] += (
        f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: The PROB_NS probability ({event.lvc_includes_neutron_star_probability}) "
        f"is out of range {gw_settings.minimum_neutron_star_probability} and {gw_settings.maximum_neutron_star_probability} so not triggering. \n"
    )

    context['reached_end'] = True

    return context


@log_event(message="BNS probability is out of range. Not triggering", level="debug")
def check_bns_probability(gw_settings, context: dict) -> dict:
    """
    Check if the binary neutron star probability is within the acceptable range.

    This function verifies if the probability of the event being a binary neutron star
    is within the defined range in the GW settings.

    Args:
        gw_settings (Dict[str, Any]): Settings specific to gravitational wave events.
        context (Dict[str, Any]): The context dictionary containing event information.

    Returns:
        Dict[str, Any]: The updated context dictionary.
    """
    if context["stop_processing"]:  # Only check if no previous condition was met
        return context

    event = context["event"]

    if event.lvc_binary_neutron_star_probability is None:
        return context
    # if event.lvc_binary_neutron_star_probability:

    if (
        event.lvc_binary_neutron_star_probability
        <= gw_settings.maximum_binary_neutron_star_probability
    ) and (
        event.lvc_binary_neutron_star_probability
        >= gw_settings.minimum_binary_neutron_star_probability
    ):
        return context

    context["stop_processing"] = True
    context["debug_bool"] = True
    context["decision_reason_log"] += (
        f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: The PROB_BNS probability ({event.lvc_binary_neutron_star_probability}) "
        f"is out of range {gw_settings.minimum_binary_neutron_star_probability} and {gw_settings.maximum_binary_neutron_star_probability} so not triggering. \n"
    )

    context['reached_end'] = True

    return context


@log_event(message="NSBH probability is out of range. Not triggering", level="debug")
def check_nsb_h_probability(gw_settings, context: dict) -> dict:
    """
    Check if the neutron star-black hole probability is within the acceptable range.

    This function verifies if the probability of the event being a neutron star-black hole
    system is within the defined range in the GW settings.

    Args:
        gw_settings: Gravitational wave settings object.
        context (Dict[str, Any]): The context dictionary containing event information.

    Returns:
        Dict[str, Any]: The updated context dictionary.
    """
    if context["stop_processing"]:  # Only check if no previous condition was met
        return context

    event = context["event"]

    if event.lvc_neutron_star_black_hole_probability is None:
        return context

    if (
        event.lvc_neutron_star_black_hole_probability
        <= gw_settings.maximum_neutron_star_black_hole_probability
    ) and (
        event.lvc_neutron_star_black_hole_probability
        >= gw_settings.minimum_neutron_star_black_hole_probability
    ):
        return context

    context["stop_processing"] = True
    context["debug_bool"] = True
    context["decision_reason_log"] += (
        f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: The PROB_NSBH probability ({event.lvc_neutron_star_black_hole_probability}) "
        f"is out of range {gw_settings.minimum_neutron_star_black_hole_probability} and {gw_settings.maximum_neutron_star_black_hole_probability} so not triggering. \n"
    )

    context['reached_end'] = True
    return context


@log_event(message="BBH probability is out of range. Not triggering", level="debug")
def check_bbh_probability(gw_settings, context: dict) -> dict:
    """
    Check if the binary black hole probability is within the acceptable range.

    This function verifies if the probability of the event being a binary black hole
    is within the defined range in the GW settings.

    Args:
        gw_settings: Gravitational wave settings object.
        context (Dict[str, Any]): The context dictionary containing event information.

    Returns:
        Dict[str, Any]: The updated context dictionary.
    """
    if context["stop_processing"]:  # Only check if no previous condition was met
        return context

    event = context["event"]

    if event.lvc_binary_black_hole_probability is None:
        return context

    if (
        event.lvc_binary_black_hole_probability
        <= gw_settings.maximum_binary_black_hole_probability
    ) and (
        event.lvc_binary_black_hole_probability
        >= gw_settings.minimum_binary_black_hole_probability
    ):
        return context

    context["stop_processing"] = True
    context["debug_bool"] = True
    context["decision_reason_log"] += (
        f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: The PROB_BBH probability ({event.lvc_binary_black_hole_probability}) "
        f"is out of range {gw_settings.minimum_binary_black_hole_probability} and {gw_settings.maximum_binary_black_hole_probability} so not triggering. \n"
    )

    context['reached_end'] = True

    return context


@log_event(
    message="Terrestrial probability is out of range. Not triggering", level="debug"
)
def check_terrestrial_probability(gw_settings, context: dict) -> dict:
    """
    Check if the terrestrial probability is within the acceptable range.

    This function verifies if the probability of the event being of terrestrial origin
    is within the defined range in the GW settings.

    Args:
        gw_settings: Gravitational wave settings object.
        context (Dict[str, Any]): The context dictionary containing event information.

    Returns:
        Dict[str, Any]: The updated context dictionary.
    """
    if context["stop_processing"]:  # Only check if no previous condition was met
        return context

    event = context["event"]

    if event.lvc_terrestial_probability is None:
        return context

    if (
        event.lvc_terrestial_probability <= gw_settings.maximum_terrestial_probability
    ) and (
        event.lvc_terrestial_probability >= gw_settings.minimum_terrestial_probability
    ):
        return context

    context["stop_processing"] = True
    context["debug_bool"] = True
    context["decision_reason_log"] += (
        f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: The PROB_Terre probability ({event.lvc_terrestial_probability}) "
        f"is out of range {gw_settings.minimum_terrestial_probability} and {gw_settings.maximum_terrestial_probability} so not triggering. \n"
    )

    context['reached_end'] = True

    return context


@log_event(message="GW significance is not observed. Not triggering", level="debug")
def check_significance(telescope_settings, context: dict) -> dict:
    """
    Check if the gravitational wave event significance meets the observation criteria.

    This function verifies if the event's significance aligns with the telescope's
    observation settings.

    Args:
        telescope_settings : Settings object related to the telescope.
        context (Dict[str, Any]): The context dictionary containing event information.

    Returns:
        Dict[str, Any]: The updated context dictionary.
    """
    if context["stop_processing"]:  # Only check if no previous condition was met
        return context

    event = context["event"]

    if (
        event.lvc_significant == True and not telescope_settings.observe_significant
    ) is False:
        return context

    # if event.lvc_significant == True and not telescope_settings.observe_significant:

    context["stop_processing"] = True
    context["debug_bool"] = True
    context["decision_reason_log"] += (
        f"{datetime.now(dt.timezone.utc)}: Event ID {event.id}: The GW significance ({event.lvc_significant}) "
        f"is not observed because observe_significant is {telescope_settings.observe_significant}. \n"
    )

    context['reached_end'] = True
    return context
