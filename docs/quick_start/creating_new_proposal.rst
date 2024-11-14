.. _creating_new_proposal:

Creating New Proposal
=====================

Overview
--------
Proposal settings model class is defined in prop_api/proposalsettings/models/proposal.py. The model consist of the proposal settings and the telescope settings. The telescope settings classes are defined in prop_api/proposalsettings/models/telescopesettings.py. The source settings classes are defined in prop_api/proposalsettings/models/sourcesettings.py. If you want change the proposal settings parameters, you need to change one of the classes.

Actual list of proposal settings models are created in the factory classes in prop_api/proposalsettings/proposalsettings_factory.py. Using the factory classes is the recommended way to create new proposal settings models and other list of models. The list of the models in the factory classes are used in the proposal api. Besides proposal settings models, other list of models are also created in the factory classes and shown in the code block below.

.. code-block::

    prop_api/proposalsettings/telescopeprojectid_factory.py       - telescope project id
    prop_api/proposalsettings/telescope_factory.py                - telescope
    prop_api/proposalsettings/eventtelescope_factory.py           - event telescope
    prop_api/proposalsettings/proposalsettings_factory.py         - proposal settings

The classes are added to the list of the models in the factory classes automatically when the classes are created. The list of the models are used in the proposal api endpoints. Please refer to the :ref:`Proposal api <prop_api_endpoints>` for the details of the api endpoints. if you need to more info about the factory classes, please check the code and :ref:`Proposal package factory classes <prop_api_factory>`

Creating New Proposal Settings Model
------------------------------------

The example of creating new proposal settings model is shown below in the code block(prop_api/proposalsettings/proposalsettings_factory.py). You can add new proposal settings models by adding the following function to the factory class. After adding the following function, you dont need to do anything else except restarting docker containers because the web application table is updated automatically when it restars. Here, the name of the new model is proposal_mwa_gw_bns_test. The telescope settings are for the MWA telescope and the source settings are for the GW source. if the telescope settings and source settings are not defined, the default values are used. Using the telescope and source settings, the proposal settings model is created. 

.. code-block::

    @property
    def proposal_mwa_gw_bns_test(self):
        # Creating the instance based on the data from id=13
        telescope_settings = MWATelescopeSettings(
            telescope=self.telescope_factory.telescope_mwa_vcs,
            maximum_position_uncertainty=0.05,
            fermi_prob=50,
            repointing_limit=10.0,
            observe_significant=True,
            start_observation_at_high_sensitivity=True,
            # MWA specific settings
            mwa_freqspecs="93,24",
            mwa_exptime=7200,
        )

        source_settings = GWSourceSettings()


        prop_settings = ProposalSettings(
            id=20,
            project_id=self.project_id_factory.telescope_project_g0094,
            proposal_id="MWA_GW_BNS_TEST",
            proposal_description="MWA triggering on LIGO-Virgo-KAGRA BNS GW events detected during O4 using a multi-beam approach and the VCS",
            priority=1,
            event_telescope=self.event_telescope_factory.event_telescope_lvc,
            testing=TriggerOnChoices.BOTH,
            source_type=SourceChoices.GW,
            telescope_settings=telescope_settings,
            source_settings=source_settings,
        )

        return prop_settings

Several factory classes are used to create the list for the event telescope, telescope and project ids. These factory classes are used in creating the new proposal settings model. 
**The id is unique** and is used to identify the proposal settings model in the database. **If the existing id is used, the existing proposal settings model is updated**.

Once the proposal settings model is created, it can be used in the proposal api immediately. To use the proposal settings model in the web application, 
**the docker container needs to be restarted**.
