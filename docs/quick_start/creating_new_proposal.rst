.. _creating_new_proposal:

Creating New Proposal
=====================

Overview
--------
Abstract/Base proposal settings model class is defined in prop_api/proposalsettings/models/proposal.py. The model consist of the proposal settings parameters and the telescope settings. The telescope settings classes are defined in prop_api/proposalsettings/models/telescopesettings.py.

Actual list of proposal settings models are created in separate directories started with prop_ and names of models in models directory. Then, its added to the factory classe in prop_api/proposalsettings/proposalsettings_factory.py. Using the factory classes is the recommended way to create new proposal settings models and other list of models. The list of the models in the factory classes are used in the proposal api. Besides proposal settings models, other list of models are also created in the factory classes and shown in the code block below.

.. code-block::

    prop_api/proposalsettings/telescopeprojectid_factory.py       - telescope project id
    prop_api/proposalsettings/telescope_factory.py                - telescope
    prop_api/proposalsettings/eventtelescope_factory.py           - event telescope
    prop_api/proposalsettings/proposalsettings_factory.py         - proposal settings

The classes are added to the list of the models in the factory classes automatically when the classes are created. The list of the models are used in the proposal api endpoints. Please refer to the :ref:`Proposal api <prop_api_endpoints>` for the details of the api endpoints. if you need to more info about the factory classes, please check the code and :ref:`Proposal package factory classes <prop_api_factory>`

Creating New Proposal Settings Model
------------------------------------

The example bare minimum new proposal settings models are created in two folders in 

.. code-block::

    prop_api/proposalsettings/models/prop_atca_test_grb
    prop_api/proposalsettings/models/prop_mwa_test_grb
    
The folder name should match the corresponding class name and proposal ID, as demonstrated in the example. Using the proposal ID, the folder is copied to the shared directory and displayed in the web application.


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
        
The variables for the parent class ProposalSettings are defined in the class variables and additional variables can be defined in the class. Please see the class for prop_mwa_gw_bns as example. All the logics can be defined in the two main functions in the class. is_worth_observing function will define three trigger variables and one log text and add them to the context dictionary. 

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

The trigger_gen_observation function is used to trigger the observation. This function is called when the is_worth_observing function returns True. This function is used to generate the trigger telescope using trigger_telescope function in telescope settings class and add it to the database on web application using save_observation function in telescope settings class. 
Also, it adds the log text to the context dictionary.

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


After creating the new proposal settings model, it needs to be added to the factory classes in prop_api/proposalsettings/proposalsettings_factory.py.


.. code-block::
    from .models.prop_atca_test_grb.model import ProposalAtcaTestGrb

    class ProposalSettingsFactory:
        ...

        @property
        def proposal_atca_test_grb(self):
            print("proposal_atca_test_grb")
            prop = ProposalAtcaTestGrb()
            return prop


Several factory classes are used to create the list for the event telescope, telescope and project ids. These factory classes are used in creating the new proposal settings model. 
**The id is unique** and is used to identify the proposal settings model in the database. **If the existing id is used, the existing proposal settings model is updated**.

Once the proposal settings model is created, it can be used in the proposal api immediately. To use the proposal settings model in the web application, 
**the update button needs to be clicked**.
Utility functions for the worth_observing function are implemented in utils_grb.py and utils_gw.py. For detailed information, please refer to the code.

Utility functions for the trigger_atca_observation function are implemented in utils_telescope_atca.py, while those for the trigger_mwa_observation function are implemented in utils_telescope_gw.py and utils_telescope_nogw.py.

Utility functions located in the proposal settings directory are specific to their corresponding model classes and do not interfere with other proposal settings models. However, utility functions located outside the proposal settings directory are shared across all proposal settings models.

If a specific utility function is needed for a new proposal settings model and requires modification, it is recommended to add the utility function to the appropriate proposal settings directory and make the necessary changes there.
