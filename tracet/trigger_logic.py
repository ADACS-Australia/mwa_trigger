import datetime
import logging
import pytz

logger = logging.getLogger(__name__)


def worth_observing_grb(
        # event values
        event_duration=None,
        fermi_most_likely_index=None,
        fermi_detection_prob=None,
        swift_rate_signif=None,
        hess_significance=None,
        pos_error=None,
        dec=None,
        # Thresholds
        event_any_duration=False,
        event_min_duration=0.256,
        event_max_duration=1.023,
        pending_min_duration_1=0.124,
        pending_max_duration_1=0.255,
        pending_min_duration_2=1.024,
        pending_max_duration_2=2.048,
        fermi_min_detection_prob=50,
        swift_min_rate_signif=0.,
        minimum_hess_significance=0.,
        maximum_hess_significance=1.,
        maximum_position_uncertainty=None,
        atca_dec_min_1=None,
        atca_dec_max_1=None,
        atca_dec_min_2=None,
        atca_dec_max_2=None,
        # Other
        proposal_telescope_id=None,
        decision_reason_log="",
        event_id=None,
    ):
    """Decide if a GRB Event is worth observing.

    Parameters
    ----------
    event_duration : `float`, optional
        The duration of the VOevent in seconds.
    fermi_most_likely_index : `int`, optional
        An index that Fermi uses to describe what sort of source the Event. GRBs are 4 so this is what we check for.
    fermi_detection_prob : `int`, optional
        A GRB detection probabilty that Fermi produces as a percentage.
    swift_rate_signif : `float`, optional
        A rate signigicance that SWIFT produces in sigma.
    event_any_duration: `Bool`, optional
        If True will trigger on an event with any duration including None. Default False.
    event_min_duration, event_max_duration : `float`, optional
        A event duration between event_min_duration and event_max_duration will trigger an observation. Default 0.256, 1.023.
    pending_min_duration_1, pending_max_duration_1 : `float`, optional
        A event duration between pending_min_duration_1 and pending_max_duration_1 will create a pending observation. Default 0.124, 0.255.
    pending_min_duration_2, pending_max_duration_2 : `float`, optional
        A event duration between pending_min_duration_2 and pending_max_duration_2 will create a pending observation. Default 1.024, 2.048.
    fermi_min_detection_prob : `float`, optional
        The minimum fermi_detection_prob to trigger or create a pending observation. Default: 50.
    swift_min_rate_signif : `float`, optional
        The minimum swift_rate_signif to trigger or create a pending observation. Default: 0.0.
    decision_reason_log : `str`, optional
        A log of all the decisions made so far so a user can understand why the source was(n't) observed. Default: "".
    event_id : `int`, optional
        An Event ID that will be recorded in the decision_reason_log. Default: None.

    Returns
    -------
    trigger_bool : `boolean`
        If True an observations should be triggered.
    debug_bool : `boolean`
        If True a debug alert should be sent out.
    pending_bool : `boolean`
        If True will create a pending observation and wait for human intervention.
    decision_reason_log : `str`
        A log of all the decisions made so far so a user can understand why the source was(n't) observed.
    """
    print('DEBUG - worth_observing_grb')
    # Setup up defaults
    trigger_bool = False
    debug_bool = False
    pending_bool = False


    if pos_error == 0.0:
    # Ignore the inaccurate event
        debug_bool = True
        decision_reason_log = f"{decision_reason_log}{datetime.datetime.utcnow()}: Event ID {event_id}: The Events positions uncertainty is 0.0 which is likely an error so not observing. \n"
    elif maximum_position_uncertainty and (pos_error > maximum_position_uncertainty):
        # Ignore the inaccurate event
        debug_bool = True
        decision_reason_log = f"{decision_reason_log}{datetime.datetime.utcnow()}: Event ID {event_id}: The Events positions uncertainty ({pos_error:.4f} deg) is greater than {maximum_position_uncertainty:.4f} so not observing. \n"
    elif proposal_telescope_id == "ATCA" and not (dec > atca_dec_min_1 and dec < atca_dec_max_1) and not (dec > atca_dec_min_2 and dec < atca_dec_max_2):
        # Ignore the inaccurate event
        debug_bool = True
        decision_reason_log = f"{decision_reason_log}{datetime.datetime.utcnow()}: Event ID {event_id}: The Events declination ({ dec }) is outside limit 1 ({ atca_dec_min_1 } < dec < {atca_dec_max_1}) or limit 2 ({ atca_dec_min_2 } < dec < {atca_dec_max_2}). \n"
    # Check the events likelyhood data
    likely_bool = False
    if fermi_most_likely_index is not None:
        # Fermi triggers have their own probability
        if fermi_most_likely_index == 4:
            logger.debug("MOST_LIKELY = GRB")
            print('DEBUG - MOST_LIKELY = GRB')
            # ignore things that don't reach our probability threshold
            if fermi_detection_prob >= fermi_min_detection_prob:
                likely_bool = True
                decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: Fermi GRB probability greater than {fermi_min_detection_prob}. \n"
            else:
                debug_bool = True
                decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: Fermi GRB probability less than {fermi_min_detection_prob} so not triggering. \n"
        else:
            logger.debug("MOST LIKELY != GRB")
            print('DEBUG - MOST LIKELY != GRB')
            debug_bool = False
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: Fermi GRB likely index not 4. \n"
    elif swift_rate_signif is not None:
        # Swift has a rate signif in sigmas
        if swift_rate_signif >= swift_min_rate_signif:
            likely_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: SWIFT rate significance ({swift_rate_signif}) >= swift_min_rate ({swift_min_rate_signif:.3f}) sigma. \n"
        else:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: SWIFT rate significance ({swift_rate_signif}) < swift_min_rate ({swift_min_rate_signif:.3f}) sigma so not triggering. \n"

    elif hess_significance is not None:
        if hess_significance <= maximum_hess_significance and hess_significance >= minimum_hess_significance:
            likely_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: HESS rate significance is {minimum_hess_significance} <= ({hess_significance:.3f}) <= {maximum_hess_significance} sigma. \n"
        else:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: Event ID {event_id}: HESS rate significance is not {minimum_hess_significance} <= ({hess_significance:.3f}) <= {maximum_hess_significance} so not triggering. \n"
    else:
        likely_bool = True
        decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: No probability metric given so assume it is a GRB. \n"
    # Check the duration of the event
    if event_any_duration and likely_bool:
        trigger_bool = True
        decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: Accepting any event duration so triggering. \n"
    elif not event_any_duration and event_duration is None:
        debug_bool = True
        decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: No event duration (None) so not triggering. \n"
    elif event_duration is not None and likely_bool:
        if event_min_duration <= event_duration <= event_max_duration:
            trigger_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: Event duration between {event_min_duration} and {event_max_duration} s so triggering. \n"
        elif pending_min_duration_1 <= event_duration <= pending_max_duration_1:
            pending_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: Event duration between {pending_min_duration_1} and {pending_max_duration_1} s so waiting for a human's decision. \n"
        elif pending_min_duration_2 <= event_duration <= pending_max_duration_2:
            pending_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: Event duration between {pending_min_duration_2} and {pending_max_duration_2} s so waiting for a human's decision. \n"
        else:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: Event duration outside of all time ranges so not triggering. \n"
    
    return trigger_bool, debug_bool, pending_bool, decision_reason_log

def worth_observing_nu(
        # event values
        antares_ranking=None,
        telescope=None,
        # Thresholds
        antares_min_ranking=2,
        # Other
        decision_reason_log="",
        event_id=None,
    ):
    """Decide if a Neutrino Event is worth observing.

    Parameters
    ----------
    antares_ranking : `int`, optional
        The rank of antaras event. Default: None.
    telescope : `int`, optional
        The rank of telescope of the event. Default: None.
    antares_min_ranking : `int`, optional
        The minimum (inclusive) rank of antaras events. Default: 2.
    decision_reason_log : `str`
        A log of all the decisions made so far so a user can understand why the source was(n't) observed. Default: "".
    event_id : `int`, optional
        An Event ID that will be recorded in the decision_reason_log. Default: None.

    Returns
    -------
    trigger_bool : `boolean`
        If True an observations should be triggered.
    debug_bool : `boolean`
        If True a debug alert should be sent out.
    pending_bool : `boolean`
        If True will create a pending observation and wait for human intervention.
    decision_reason_log : `str`
        A log of all the decisions made so far so a user can understand why the source was(n't) observed.
    """
    # Setup up defaults
    trigger_bool = False
    debug_bool = False
    pending_bool = False

    if telescope == "Antares":
        # Check the Antares ranking
        if antares_ranking <= antares_min_ranking:
            trigger_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The Antares ranking ({antares_ranking}) is less than or equal to {antares_min_ranking} so triggering. \n"
        else:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The Antares ranking ({antares_ranking}) is greater than {antares_min_ranking} so not triggering. \n"
    else:
        trigger_bool = True
        decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: No thresholds for non Antares telescopes so triggering. \n"

    return trigger_bool, debug_bool, pending_bool, decision_reason_log

def worth_observing_gw(
        # event values
        telescope=None,
        lvc_significant=None,
        lvc_binary_neutron_star_probability=None,
        lvc_neutron_star_black_hole_probability=None,
        lvc_binary_black_hole_probability=None,
        lvc_terrestial_probability=None,
        lvc_includes_neutron_star_probability=None,
        lvc_false_alarm_rate=None,
        # Thresholds
        minimum_neutron_star_probability=None,
        maximum_neutron_star_probability=None,
        minimum_binary_neutron_star_probability=None,
        maximum_binary_neutron_star_probability=None,
        minimum_neutron_star_black_hole_probability=None,
        maximum_neutron_star_black_hole_probability=None,
        minimum_binary_black_hole_probability=None,
        maximum_binary_black_hole_probability=None,
        minimum_terrestial_probability=None,
        maximum_terrestial_probability=None,
        observe_significant=None,
        event_type=None,
        minimum_false_alarm_rate=None,
        # Other
        decision_reason_log="",
        event_observed=datetime.datetime.now(datetime.timezone.utc),
        event_id=None,
        lvc_instruments=None
    ):
    """Decide if a Gravity Wave Event is worth observing.

    Parameters
    ----------
    telescope : `str`, optional
        The telescope used for the event. Default: None.
    lvc_significant : `bool`, optional
        The calculated significance of the event. Default: None.
    lvc_binary_neutron_star_probability : `float`, optional
        The terrestial probability of gw event. Default: None.
    lvc_neutron_star_black_hole_probability : `float`, optional
        The terrestial probability of gw event. Default: None.
    lvc_binary_black_hole_probability : `float`, optional
        The terrestial probability of gw event. Default: None.
    lvc_terrestial_probability : `float`, optional
        The terrestial probability of gw event. Default: None
    lvc_includes_neutron_star_probability : `float`, optional
        The terrestial probability of gw event. Default: None
    
    minimum_neutron_star_probability : `float`, optional
        The minimum neutron star probability. Default: 0.01.
    maximum_neutron_star_probability : `float`, optional
        The maximum neutron star probability. Default: 1.00.
    minimum_binary_neutron_star_probability : `float`, optional
        The minimum binary neutron star probability. Default: 0.01.
    maximum_binary_neutron_star_probability : `float`, optional
        The maximum binary neutron star probability. Default: 1.00.
    minimum_terrestial_probability : `float`, optional
        The minimum terrestial probability. Default: 0.95.
    maximum_terrestial_probability : `float`, optional
        The maximum terrestial probability. Default: 0.95.
    observe_significant : `bool`, optional
        Observe significant events. Default: True.
    decision_reason_log : `str`
        A log of all the decisions made so far so a user can understand why the source was(n't) observed. Default: "".
    event_observed : `date`, optional
        Time of the event. Default: Date now.
    event_id : `int`, optional
        An Event ID that will be recorded in the decision_reason_log. Default: None.

    Returns
    -------
    trigger_bool : `boolean`
        If True an observations should be triggered.
    debug_bool : `boolean`
        If True a debug alert should be sent out.
    pending_bool : `boolean`
        If True will create a pending observation and wait for human intervention.
    decision_reason_log : `str`
        A log of all the decisions made so far so a user can understand why the source was(n't) observed.
    """
    # Setup up defaults
    trigger_bool = False
    debug_bool = False
    pending_bool = False

    # Get exponent
    # lvc_false_alarm_rate = None | "3.218261352069347-10" | "0.0001"
    if lvc_false_alarm_rate and minimum_false_alarm_rate:
        try:
            FAR = float(lvc_false_alarm_rate)
            FARThreshold = float(minimum_false_alarm_rate)
        except Exception as e:
            debug_bool = True
            decision_reason_log += f'{datetime.datetime.utcnow()}: Event ID {event_id}: The event FAR ({lvc_false_alarm_rate}) or proposal FAR ({minimum_false_alarm_rate}) could not be processed so not triggering. \n'
       
    print(f"\nLogic event_type: {event_type}")
    print(f"\nLogic lvc_instruments: {lvc_instruments}")
    # Check alert is less than 3 hours from the event time
    three_hours_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=3)
    if(event_observed.replace(tzinfo=datetime.timezone.utc) < three_hours_ago):
        debug_bool = True
        decision_reason_log += f'{datetime.datetime.utcnow()}: Event ID {event_id}: The event time {event_observed.strftime("%Y-%m-%dT%H:%M:%S+0000")} is more than 3 hours ago {three_hours_ago.strftime("%Y-%m-%dT%H:%M:%S+0000")} so not triggering. \n'
    elif(lvc_instruments != None and len(lvc_instruments.split(',')) < 2):
        debug_bool = True
        decision_reason_log += f'{datetime.datetime.utcnow()}: Event ID {event_id}: The event has only {lvc_instruments} so not triggering. \n'
    elif telescope == "LVC" and event_type == "EarlyWarning":
        trigger_bool = True
        decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: Early warning, no information so triggering. \n"
    elif telescope == "LVC" and event_type == "Retraction":
        trigger_bool = True
        decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: Retraction, scheduling no capture observation (WIP, ignoring for now). \n"
    elif telescope == "LVC":

        # PROB_NS
        if lvc_false_alarm_rate and minimum_false_alarm_rate and FAR < FARThreshold:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The FAR is {lvc_false_alarm_rate} which is less than {minimum_false_alarm_rate} so not triggering. \n"
        elif lvc_includes_neutron_star_probability > maximum_neutron_star_probability:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The PROB_NS probability ({lvc_includes_neutron_star_probability}) is greater than {maximum_neutron_star_probability} so not triggering. \n"
        elif lvc_includes_neutron_star_probability < minimum_neutron_star_probability:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The PROB_NS probability ({lvc_includes_neutron_star_probability}) is less than {minimum_neutron_star_probability} so not triggering. \n"
        elif lvc_binary_neutron_star_probability > maximum_binary_neutron_star_probability:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The PROB_BNS probability ({lvc_binary_neutron_star_probability}) is greater than {maximum_binary_neutron_star_probability} so not triggering. \n"
        elif lvc_binary_neutron_star_probability < minimum_binary_neutron_star_probability:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The PROB_BNS probability ({lvc_binary_neutron_star_probability}) is less than {minimum_binary_neutron_star_probability} so not triggering. \n"
        elif lvc_neutron_star_black_hole_probability > maximum_neutron_star_black_hole_probability:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The PROB_NSBH probability ({lvc_neutron_star_black_hole_probability}) is greater than {maximum_neutron_star_black_hole_probability} so not triggering. \n"
        elif lvc_neutron_star_black_hole_probability < minimum_neutron_star_black_hole_probability:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The PROB_NSBH probability ({lvc_neutron_star_black_hole_probability}) is less than {maximum_neutron_star_black_hole_probability} so not triggering. \n"
        elif lvc_binary_black_hole_probability > maximum_binary_black_hole_probability:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The PROB_BBH probability ({lvc_binary_black_hole_probability}) is greater than {maximum_binary_black_hole_probability} so not triggering. \n"
        elif lvc_binary_black_hole_probability < minimum_binary_black_hole_probability:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The PROB_BBH probability ({lvc_binary_black_hole_probability}) is less than {minimum_binary_black_hole_probability} so not triggering. \n"
        elif lvc_terrestial_probability > maximum_terrestial_probability:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The PROB_Terre probability ({lvc_terrestial_probability}) is greater than {maximum_terrestial_probability} so not triggering. \n"
        elif lvc_terrestial_probability< minimum_terrestial_probability:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The PROB_Terre probability ({lvc_terrestial_probability}) is less than {minimum_terrestial_probability} so not triggering. \n"
        
        elif lvc_significant == True and not observe_significant:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The GW significance ({lvc_significant}) is not observed because observe_significant is {observe_significant}. \n"
            
        else:
            trigger_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The probability looks good so triggering. \n"


    return trigger_bool, debug_bool, pending_bool, decision_reason_log