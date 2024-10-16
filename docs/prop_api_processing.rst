Utility Functions for Main Processing
=====================================

The utility functions for main processing are stored in the `utils` module.

After receiving a new or existing proposal with other associated data, the following functions are used to process the data.

Main functions for Processing
---------------------------------

The first function to be called is `process_all_proposals`. This function is main function that orchestrates the processing of all proposals or new proposals
calling other functions to do the job. 

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

