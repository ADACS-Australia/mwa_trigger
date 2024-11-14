.. _prop_api_models:

Proposal Package Models
=======================

The `models` module in `proposalsettings` defines the data models used for proposals and telescopes.

.. toctree::
   :maxdepth: 1
   :caption: Model Documentation:

   proposal_model
   telescope_settings_model
   source_settings_model
   other_models

1. :doc:`ProposalSettings <proposal_model>`
   
   Stores settings related to proposals, including methods for determining observation worthiness and triggering observations.

2. :doc:`TelescopeSettings <telescope_settings_model>`
   
   Manages the configuration of telescopes, storing telescope-related parameters and data.

3. :doc:`SourceSettings <source_settings_model>`
   
   Defines settings for sources being observed, including logic for determining observation worthiness and triggering observations based on telescope type.

4. :doc:`Other Models <other_models>`
   
   Contains documentation for additional models in the proposal package.
