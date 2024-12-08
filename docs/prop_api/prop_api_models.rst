.. _prop_api_models:

Proposal Package Models
=======================

The `models` module in `proposalsettings` defines the data models used for proposals and telescopes.

.. toctree::
   :maxdepth: 1
   :caption: Model Documentation:

   proposal_model
   telescope_settings_model
   proposal_settings_children
   other_models

1. :doc:`ProposalSettings <proposal_model>`
   
   Parent class for proposals which hold parameters and methods for determining observation worthiness and triggering observations.

2. :doc:`TelescopeSettings <telescope_settings_model>`
   
   Manages the configuration of telescopes, storing telescope-related parameters and data.

3. :doc:`Proposal Settings Children Classes <proposal_settings_children>`
   
   Defines actual proposal settings for parameters and methods including logic for determining observation worthiness and triggering observations based on telescope type.

4. :doc:`Other Models <other_models>`
   
   Contains documentation for additional models in the proposal package.
