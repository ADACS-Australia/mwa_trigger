from datetime import datetime, timedelta
from functools import partial
from typing import Tuple, Union


# Initialize the context with the event and defaults
def initialize_context(event, kwargs) -> dict:
    # print('DEBUG - event:', event)

    return {
        "event": event,
        "decision_reason_log": kwargs.get("decision_reason_log", ""),
        "trigger_bool": False,
        "debug_bool": False,  # This remains for its original purpose
        "pending_bool": False,
        "FAR": None,
        "FARThreshold": None,
        "stop_processing": False,  # New flag to control short-circuiting
    }


# Process the False Alarm Rate (FAR)
def process_false_alarm_rate(self, context) -> dict:

    event = context["event"]
    if event.lvc_false_alarm_rate and self.maximum_false_alarm_rate:
        try:
            context["FAR"] = float(event.lvc_false_alarm_rate)
            context["FARThreshold"] = float(self.maximum_false_alarm_rate)
        except Exception as e:
            context["debug_bool"] = True
            context["stop_processing"] = True
            context["decision_reason_log"] += (
                f"{datetime.utcnow()}: Event ID {event.id}: The event FAR ({event.lvc_false_alarm_rate}) "
                f"or proposal FAR ({self.maximum_false_alarm_rate}) could not be processed so not triggering. \n"
            )
    return context


def update_event_parameters(context):
    event = context["event"]
    if event.telescope == "LVC" and event.event_type == "EarlyWarning":
        context["trigger_bool"] = True  # Always trigger on Early Warning events
        event.lvc_binary_neutron_star_probability = 0.97
        event.lvc_neutron_star_black_hole_probability = 0.01
        event.lvc_binary_black_hole_probability = 0.01
        event.lvc_terrestial_probability = 0.01

        context["event"] = event

    return context


# Check event time against a threshold of 2 hours ago
def check_event_time(context) -> dict:
    event = context["event"]
    two_hours_ago = datetime.utcnow() - timedelta(hours=2)
    if event.event_observed < two_hours_ago:
        context["stop_processing"] = True
        context["trigger_bool"] = False
        context["decision_reason_log"] += (
            f'{datetime.utcnow()}: Event ID {event.id}: The event time {event.event_observed.strftime("%Y-%m-%dT%H:%M:%S+0000")} '
            f'is more than 2 hours ago {two_hours_ago.strftime("%Y-%m-%dT%H:%M:%S+0000")} so not triggering. \n'
        )

    return context


# Check the number of LVC instruments involved
def check_lvc_instruments(context) -> dict:
    # Short-circuit if a previous condition was met
    if context["stop_processing"]:
        return context

    event = context["event"]
    if event.lvc_instruments and len(event.lvc_instruments.split(",")) < 2:
        context["stop_processing"] = True
        context["debug_bool"] = True
        context[
            "decision_reason_log"
        ] += f"{datetime.utcnow()}: Event ID {event.id}: The event has only {event.lvc_instruments} so not triggering. \n"
    return context


# Handle specific event types and telescope
def handle_event_types(context) -> dict:
    # Short-circuit if a previous condition was met
    if context["stop_processing"]:
        return context

    event = context["event"]
    if event.telescope == "LVC" and event.event_type == "Retraction":
        context["stop_processing"] = True
        context["debug_bool"] = True
        context[
            "decision_reason_log"
        ] += f"{datetime.utcnow()}: Event ID {event.id}: Retraction, scheduling no capture observation (WIP, ignoring for now). \n"

    return context


# Check all probabilities by chaining individual checks with short-circuiting
def check_probabilities(telescope_settings, self, context) -> dict:
    if context["stop_processing"]:
        return context

    event = context["event"]
    if event.telescope == "LVC":
        context = check_far_against_threshold(context)
        context = check_ns_probability(self, context)
        context = check_bns_probability(self, context)
        context = check_nsb_h_probability(self, context)
        context = check_bbh_probability(self, context)
        context = check_terrestrial_probability(self, context)
        context = check_significance(telescope_settings, context)

    # If no conditions prevent triggering, consider it worth observing
    if not context["stop_processing"]:
        context["trigger_bool"] = True
        context[
            "decision_reason_log"
        ] += f"{datetime.utcnow()}: Event ID {context['event'].id}: The probability looks good so triggering. \n"

    return context


# Check FAR against the threshold
def check_far_against_threshold(context) -> dict:
    if context["stop_processing"]:
        return context

    if context["FAR"] is not None and context["FARThreshold"] is not None:
        if context["FAR"] > context["FARThreshold"]:
            context["stop_processing"] = True
            context["debug_bool"] = True
            context["decision_reason_log"] += (
                f"{datetime.utcnow()}: Event ID {context['event'].id}: The FAR is {context['FAR']} "
                f"which is greater than the threshold {context['FARThreshold']} so not triggering. \n"
            )
    return context


# Check individual probabilities and short-circuit if a condition is met
def check_ns_probability(self, context) -> dict:
    if context["stop_processing"]:
        return context

    event = context["event"]
    if event.lvc_includes_neutron_star_probability:
        if (
            event.lvc_includes_neutron_star_probability
            > self.maximum_neutron_star_probability
        ):
            context["stop_processing"] = True
            context["debug_bool"] = True
            context["decision_reason_log"] += (
                f"{datetime.utcnow()}: Event ID {event.id}: The PROB_NS probability ({event.lvc_includes_neutron_star_probability}) "
                f"is greater than {self.maximum_neutron_star_probability} so not triggering. \n"
            )
        elif (
            event.lvc_includes_neutron_star_probability
            < self.minimum_neutron_star_probability
        ):
            context["stop_processing"] = True
            context["debug_bool"] = True
            context["decision_reason_log"] += (
                f"{datetime.utcnow()}: Event ID {event.id}: The PROB_NS probability ({event.lvc_includes_neutron_star_probability}) "
                f"is less than {self.minimum_neutron_star_probability} so not triggering. \n"
            )
    return context


def check_bns_probability(self, context) -> dict:
    if context["stop_processing"]:  # Only check if no previous condition was met
        return context

    event = context["event"]
    if event.lvc_binary_neutron_star_probability:

        if (
            event.lvc_binary_neutron_star_probability
            > self.maximum_binary_neutron_star_probability
        ):
            context["stop_processing"] = True
            context["debug_bool"] = True
            context["decision_reason_log"] += (
                f"{datetime.utcnow()}: Event ID {event.id}: The PROB_BNS probability ({event.lvc_binary_neutron_star_probability}) "
                f"is greater than {self.maximum_binary_neutron_star_probability} so not triggering. \n"
            )
        elif (
            event.lvc_binary_neutron_star_probability
            < self.minimum_binary_neutron_star_probability
        ):
            context["stop_processing"] = True
            context["debug_bool"] = True
            context["decision_reason_log"] += (
                f"{datetime.utcnow()}: Event ID {event.id}: The PROB_BNS probability ({event.lvc_binary_neutron_star_probability}) "
                f"is less than {self.minimum_binary_neutron_star_probability} so not triggering. \n"
            )

    return context


def check_nsb_h_probability(self, context) -> dict:
    if context["stop_processing"]:  # Only check if no previous condition was met
        return context

    event = context["event"]
    if event.lvc_neutron_star_black_hole_probability:
        if (
            event.lvc_neutron_star_black_hole_probability
            > self.maximum_neutron_star_black_hole_probability
        ):
            context["stop_processing"] = True
            context["debug_bool"] = True
            context["decision_reason_log"] += (
                f"{datetime.utcnow()}: Event ID {event.id}: The PROB_NSBH probability ({event.lvc_neutron_star_black_hole_probability}) "
                f"is greater than {self.maximum_neutron_star_black_hole_probability} so not triggering. \n"
            )
        elif (
            event.lvc_neutron_star_black_hole_probability
            < self.minimum_neutron_star_black_hole_probability
        ):
            context["stop_processing"] = True
            context["debug_bool"] = True
            context["decision_reason_log"] += (
                f"{datetime.utcnow()}: Event ID {event.id}: The PROB_NSBH probability ({event.lvc_neutron_star_black_hole_probability}) "
                f"is less than {self.minimum_neutron_star_black_hole_probability} so not triggering. \n"
            )
    return context


def check_bbh_probability(self, context) -> dict:
    if not context["stop_processing"]:  # Only check if no previous condition was met
        return context

    event = context["event"]
    if event.lvc_binary_black_hole_probability:

        if (
            event.lvc_binary_black_hole_probability
            > self.maximum_binary_black_hole_probability
        ):
            context["stop_processing"] = True
            context["debug_bool"] = True
            context["decision_reason_log"] += (
                f"{datetime.utcnow()}: Event ID {event.id}: The PROB_BBH probability ({event.lvc_binary_black_hole_probability}) "
                f"is greater than {self.maximum_binary_black_hole_probability} so not triggering. \n"
            )
        elif (
            event.lvc_binary_black_hole_probability
            < self.minimum_binary_black_hole_probability
        ):
            context["stop_processing"] = True
            context["debug_bool"] = True
            context["decision_reason_log"] += (
                f"{datetime.utcnow()}: Event ID {event.id}: The PROB_BBH probability ({event.lvc_binary_black_hole_probability}) "
                f"is less than {self.minimum_binary_black_hole_probability} so not triggering. \n"
            )
    return context


def check_terrestrial_probability(self, context) -> dict:
    if not context["stop_processing"]:  # Only check if no previous condition was met
        return context

    event = context["event"]
    if event.lvc_terrestial_probability:
        if event.lvc_terrestial_probability > self.maximum_terrestial_probability:
            context["stop_processing"] = True
            context["debug_bool"] = True
            context["decision_reason_log"] += (
                f"{datetime.utcnow()}: Event ID {event.id}: The PROB_Terre probability ({event.lvc_terrestial_probability}) "
                f"is greater than {self.maximum_terrestial_probability} so not triggering. \n"
            )
        elif event.lvc_terrestial_probability < self.minimum_terrestial_probability:
            context["stop_processing"] = True
            context["debug_bool"] = True
            context["decision_reason_log"] += (
                f"{datetime.utcnow()}: Event ID {event.id}: The PROB_Terre probability ({event.lvc_terrestial_probability}) "
                f"is less than {self.minimum_terrestial_probability} so not triggering. \n"
            )
    return context


def check_significance(telescope_settings, context) -> dict:
    if context["stop_processing"]:  # Only check if no previous condition was met
        return context

    event = context["event"]
    if event.lvc_significant == True and not telescope_settings.observe_significant:
        context["stop_processing"] = True
        context["debug_bool"] = True
        context["decision_reason_log"] += (
            f"{datetime.utcnow()}: Event ID {event.id}: The GW significance ({event.lvc_significant}) "
            f"is not observed because observe_significant is {telescope_settings.observe_significant}. \n"
        )
    return context
