.. _creating_new_proposal:

Creating New Proposal
=====================

Overview
--------
The abstract/base class for proposal settings models is defined in ``prop_api/proposalsettings/models/proposal.py``. This model includes both the proposal settings parameters and the telescope settings. The classes for telescope settings are defined separately in ``prop_api/proposalsettings/models/telescopesettings.py``.

The current list of proposal settings models is organized into separate directories, each prefixed with ``prop_``, while the models themselves reside in the ``models`` directory. These models are then registered in the factory class located at ``prop_api/proposalsettings/proposalsettings_factory.py``.

Using factory classes is the recommended approach for creating new proposal settings models and other related models. The models listed in the factory classes are integral to the proposal API. In addition to proposal settings models, other related models are also defined and managed within the factory classes, as illustrated in the code block below.

.. code-block::

    prop_api/proposalsettings/telescopeprojectid_factory.py       - telescope project id
    prop_api/proposalsettings/telescope_factory.py                - telescope
    prop_api/proposalsettings/eventtelescope_factory.py           - event telescope
    prop_api/proposalsettings/proposalsettings_factory.py         - proposal settings

After new classes are created and added to the factory class, they are automatically used in the proposal API endpoints. Using the button on web application, the new proposal settings model is added to the database.  For more details about the API endpoints, refer to the :ref:`Proposal api <prop_api_endpoints>` for the details of the api endpoints. To learn more about the factory classes, see the code and :ref:`Proposal package factory classes <prop_api_factory>`.

Creating New Proposal Settings Model
------------------------------------

Example bare-minimum proposal settings models are created in the following two folders in 

.. code-block::

    prop_api/proposalsettings/models/prop_atca_test_grb
    prop_api/proposalsettings/models/prop_mwa_test_grb
    
The folder name should match the corresponding class name and proposal ID, as shown in the example. When the update button is clicked, the folder is copied to the shared directory between the web and API containers using the proposal ID and is displayed in the web application.

.. code-block::

    models/prop_atca_test_grb/
        > model.py

.. code-block::

    class ProposalAtcaTestGrb(ProposalSettings):
    
        # Class variables
        streams: List[str] = [
            "SWIFT_BAT_GRB_POS",
        ]

        version: str = "1.0.0"
        id: int = 20
        proposal_id: str = "ATCA_test_GRB"
        
The variables for the parent ``class ProposalSettings`` are defined as class variables, with the option to add additional variables within the class. For an example, refer to the ``prop_mwa_gw_bns`` class. All logic can be implemented in the class's two main functions. The ``is_worth_observing`` function defines three trigger variables and one log message, adding them to the context dictionary. 

.. code-block::

    @log_context(prefix="prop_atca_test_grb_worth_observing")
    def is_worth_observing(self, context: Dict, **kwargs) -> Dict:
    
        print(f"DEBUG - START context keys: {context.keys()}")
        event = context["event"]

        # returning three boolean values and log text
        context["trigger_bool"] = True
        context["debug_bool"] = False
        context["pending_bool"] = False
        context["decision_reason_log"] = "This is a test GRB"

        return context

The ``trigger_gen_observation`` function is responsible for initiating the observation process. 
It is called when the ``is_worth_observing`` function returns ``True``. This function uses the 
``trigger_telescope`` method from the telescope settings class to generate the telescope trigger 
and saves it to the database in the web application using the ``save_observation`` method from 
the same class. Additionally, it adds a log message to the context dictionary.

.. code-block::

    def trigger_gen_observation(self, context: Dict, **kwargs) -> Dict[str, str]:
    
        print(f"DEBUG - START context keys: {context.keys()}")

        (context["decision"], context["decision_reason_log"], context["obsids"]) = (
            self.telescope_settings.trigger_telescope(context)
        )

        for obsid in context["obsids"]:
            saved_atca_obs = self.telescope_settings.save_observation(
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


After creating a new proposal settings model, it must be registered in the factory classes located at ``prop_api/proposalsettings/proposalsettings_factory.py``.


.. code-block::

    from .models.prop_atca_test_grb.model import ProposalAtcaTestGrb

    ...

    class ProposalSettingsFactory:
        ...

        @property
        def proposal_atca_test_grb(self):
            print("proposal_atca_test_grb")
            prop = ProposalAtcaTestGrb()
            return prop

Several factory classes are utilized to generate lists for event telescope IDs, telescope IDs, and project IDs. These factory classes play a key role in creating new proposal settings models.

**The ID is unique** and serves to identify the proposal settings model in the database. **If an existing ID is used, the corresponding proposal settings model will be updated instead of creating a new one.**


Once a proposal settings model is created, it can be immediately used in the proposal API. To enable its use in the web application, **the update button must be clicked**.

Utility functions related to the ``worth_observing`` function are implemented in ``utils_grb.py`` and ``utils_gw.py``. For more details, please refer to the corresponding code.

For the ``trigger_atca_observation`` function, utility functions are implemented in ``utils_telescope_atca.py``. Similarly, utility functions for the ``trigger_mwa_observation`` function are implemented in ``utils_telescope_gw.py`` and ``utils_telescope_nogw.py``.

Utility functions located in the proposal settings directory are specific to their corresponding model classes and do not interfere with other proposal settings models. However, utility functions located outside the proposal settings directory are shared across all proposal settings models.

If a specific utility function is needed for a new proposal settings model and requires modification, it is recommended to add the utility function to the appropriate proposal settings directory and make the necessary changes there.

* Utility functions within the proposal settings directory are specific to their respective model classes and do not interfere with other models.

* Utility functions located outside the proposal settings directory are shared among all proposal settings models.

If a new proposal settings model requires a specific utility function with modifications, it is recommended to place the function in the relevant proposal settings directory and apply the necessary changes there.