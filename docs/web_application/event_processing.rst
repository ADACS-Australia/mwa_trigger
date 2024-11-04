Event Processing
================

Overview
--------
TraceT currently uses a single event broker, but more can easily be added. The twistd_comet_wrapper.py should always be running, and its status can be seen on the homepage. The twistd comet broker listens for VOEvents, and each time it receives one, it uses upload_xml.py to parsed the event and upload it to the Event model.

Event Processing Flow
-------------------
Every time an event is added to the database, this signals the group_trigger function in webapp_tracet/trigger_app/signals.py. This will group events by their trig_id and then loop over the ProposalSettings model objects to see if any proposals want to observe this type of object. If event is new event, the event group is created and the event is added to it. The event group is then linked to the event. Also, the new proposal decisions are created. After this, the request is made to the proposal API to process the event and proposals. 

.. code-block::

    start_time = time.time()

    context = utils_signals.log_initial_debug_info(instance)

    context = utils_signals.prepare_event_data(context)

    context = utils_signals.update_or_create_event_group(context)

    context = utils_signals.link_event_to_group(context)

    context = utils_signals.check_if_ignored(context)
    if context is None:
        return

    context = utils_signals.calculate_sky_coordinates(context)

    # print(context)
    context = utils_signals.process_all_proposals(context)
    
    response = utils_api.make_process_all_proposals_request(context) 

The api request is defined in webapp_tracet/trigger_app/utils/utils_api.py. The payload is a dictionary with the data from the Event, EventGroup, ProposalDecision, and if the event is new, the event coordinates are also included. 

.. code-block::

    payload = {
        "prop_decs": prop_decs_data_str,
        "voevents": voevents_data_str,
        "event": event_data_str,
        "event_group": event_group_data_str,
        "prop_decs_exist": context["prop_decs_exist"]
    }

    if context.get("event_coord"):
        event_coord_data_str = json.loads(SkyCoordSchema.from_skycoord(context["event_coord"]).json())
        payload["event_coord"] = event_coord_data_str


After the proposals are processed, the proposal API returns a dictionary with the results and updated multiple tables including Event,EventGroup, and ProposalDecision. The new row will be added to the Observation table. 