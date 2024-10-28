Proposal API Endpoints
======================

This section describes the API endpoints available in the TraceT Proposal API.

The first function to be called is `api_process_all_proposals`. This function is main api function that receives the data from the web app and calls main processing function `process_all_proposals` in utils_process. Processing is done in a series of steps that are all handled in utils_process.

.. code-block:: python

    prop_decs_pyd = [
        ProposalDecisionSchema(**prop_dec.dict()) for prop_dec in data.prop_decs
    ]

    prop_decs_pyd_tmp = []
    for prop_dec_pyd in prop_decs_pyd:
        proposal = utils_api.get_proposal_object(prop_dec_pyd.proposal)
        prop_dec_pyd.proposal = proposal
        prop_decs_pyd_tmp.append(prop_dec_pyd)

    prop_decs_pyd = prop_decs_pyd_tmp

    voevents_pyd = [EventSchema(**voevent.dict()) for voevent in data.voevents]

    event_pyd = EventSchema(**data.event.dict())

    event_group_pyd = EventGroupSchema(**data.event_group.dict())

    if data.event_coord:
        event_coord = SkyCoordSchema(**data.event_coord.dict()).to_skycoord()
    else:
        event_coord = None

    context_all = {
        "event": event_pyd,
        "prop_decs": prop_decs_pyd,
        "voevents": voevents_pyd,
        "prop_decs_exist": data.prop_decs_exist,
        "event_group": event_group_pyd,
        "event_coord": event_coord,
    }

    context = utils_process.process_all_proposals(context_all)


api_process_all_proposals
~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: api_process_all_proposals(request, data: AllProposalsProcessRequest)

   Process all proposals based on the provided data.

   :param AllProposalsProcessRequest data: The request data containing proposal decisions, events, and other related information.
   :return: A dictionary containing the processing result.
   :rtype: Dict[str, Union[bool, str]]

get_telescopes
~~~~~~~~~~~~~~

.. py:function:: get_telescopes(request)

   Retrieve a list of all telescopes.

   :return: A list of all telescope objects.
   :rtype: List[Telescope]

get_event_telescopes
~~~~~~~~~~~~~~~~~~~~

.. py:function:: get_event_telescopes(request)

   Retrieve a list of all event telescopes.

   :return: A list of all event telescope objects.
   :rtype: List[EventTelescope]

get_event_telescope_by_name
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: get_event_telescope_by_name(request, name: str)

   Retrieve an event telescope by its name.

   :param str name: The name of the event telescope.
   :return: The event telescope object with the specified name.
   :rtype: EventTelescope
   :raises HTTPException: If the event telescope is not found.

get_telescope_project_ids
~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: get_telescope_project_ids(request)

   Retrieve a list of all telescope project IDs.

   :return: A list of all telescope project ID objects.
   :rtype: List[TelescopeProjectId]

get_proposalsettings
~~~~~~~~~~~~~~~~~~~~

.. py:function:: get_proposalsettings(request)

   Retrieve a list of all proposal settings.

   :return: A list of all proposal settings objects.
   :rtype: List[ProposalSettings]

get_proposalsettings_by_id
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: get_proposalsettings_by_id(request, id: int)

   Retrieve a proposal settings object by its ID.

   :param int id: The ID of the proposal settings.
   :return: The proposal settings object with the specified ID.
   :rtype: ProposalSettings
   :raises HTTPException: If the proposal settings are not found.


Authentication
--------------

Most endpoints in this API require authentication using JWT (JSON Web Tokens).
