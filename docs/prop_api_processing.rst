Utility Functions for Main Processing
=====================================

The utility functions for main processing are stored in the `utils` module.

After receiving a new or existing proposal with other associated data, the following functions are used to process the data.

Main functions for Processing
---------------------------------

The first function to be called is `process_all_proposals`. This function is main function that orchestrates the processing of all proposals or new proposals
calling other functions to do the job. It will loop through all the proposals and see if it's worth observing. If it is will trigger an observation and send off the relevant alerts and update the proposal decision and event group.

.. code-block:: python

        if context["prop_decs_exist"]:
            logger.info(
                "Loop over all proposals settings and see if it's worth reobserving"
            )
            context = process_proposal_decision(context)
        else:
            logger.info("First unignored event")
            context = process_new_proposal_decision(context)

        context = trigger_repointing(context)

        context = check_worth_observing(context)

        context = make_trigger_decision(context)

        result = utils_api.update_proposal_decision(
            prop_dec_pyd.id, context["decision"], context["decision_reason_log"]
        )

        result = utils_api.trigger_alerts(context)


.. automodule:: prop_api.proposalsettings.utils.utils_process
    :undoc-members:
    :show-inheritance:

.. autofunction:: prop_api.proposalsettings.utils.utils_process.process_all_proposals   
.. autofunction:: prop_api.proposalsettings.utils.utils_process.process_proposal_decision
.. autofunction:: prop_api.proposalsettings.utils.utils_process.process_new_proposal_decision
.. autofunction:: prop_api.proposalsettings.utils.utils_process.update_event_group


Other auxiliary functions can be found in the `utils_process` module.

Functions for Checking Worth Observing and calling Trigger Decision
--------------------------------------------------------------------

The following functions are used to check if the proposal is worth observing and to make the trigger decision and called in utils_process.process_all_proposals function. The first function(check_worth_observing) is calling the previously implemented proposal_worth_observing function in signal.py. The refactored proposal_worth_observing function is calling the main function(is_worth_observing) implemented in proposal model(old tracet function).

.. code-block:: python

    elif (
            prop_dec.proposal.source_type == prop_dec.event_group_id.source_type
            and prop_dec.event_group_id.source_type in ["GRB", "GW", "NU"]
        ):
            print(prop_dec.proposal.id)
            (
                trigger_bool,
                debug_bool,
                pending_bool,
                decision_reason_log,
            ) = prop_dec.proposal.is_worth_observing(
                event,
                dec=prop_dec.dec,
                decision_reason_log=decision_reason_log,
                prop_dec=prop_dec,
            )
            proj_source_bool = True


is_worth_observing function is explained in models part.

.. automodule:: prop_api.proposalsettings.utils.utils_worth_observing
    :undoc-members:
    :show-inheritance:

.. autofunction:: prop_api.proposalsettings.utils.utils_worth_observing.check_worth_observing
.. autofunction:: prop_api.proposalsettings.utils.utils_worth_observing.proposal_worth_observing
.. autofunction:: prop_api.proposalsettings.utils.utils_worth_observing.make_trigger_decision
.. autofunction:: prop_api.proposalsettings.utils.utils_worth_observing.trigger_repointing

Functions for interacting with the web app
-----------------------------------------

The following functions are used to interact with the web app. 

.. automodule:: prop_api.proposalsettings.utils.utils_api
    :undoc-members:
    :show-inheritance:

.. autofunction:: prop_api.proposalsettings.utils.utils_api.update_proposal_decision
.. autofunction:: prop_api.proposalsettings.utils.utils_api.trigger_alerts
.. autofunction:: prop_api.proposalsettings.utils.utils_api.update_event_group

Other auxiliary functions can be found in the `utils_api` module.

