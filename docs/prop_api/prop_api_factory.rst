
.. _prop_api_factory:

Proposal Package Factory Classes
================================

The `Factory Classes` module in `proposalsettings` contains classes for creating specific instances. The first class is `ProposalSettingsFactory` which creates a `ProposalSettings` object. ProposalSettings object can be added and deleted.
These are active proposal settings and uploaded to the web app database when the docker container starts. If the proposal setting is deleted from this list, the web application will tag the proposal setting as inactive and will not issue new proposals with the deleted proposal settings. However, the deleted proposal settings are used in the web application since they have been used in existing observations. Keep this in mind that proposal settings are not deleted from the web application database and the proposal settings have unique ids. If you use the deleted proposal settings id, you are updating the old proposal settings and making it active.


.. automodule:: prop_api.proposalsettings.proposalsettings_factory
    :members:
    :undoc-members:
    :show-inheritance:
    :special-members: __init__
    :exclude-members: Config, classConfig,model_computed_fields, model_config, model_fields

.. automodule:: prop_api.proposalsettings.telescope_factory
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: prop_api.proposalsettings.eventtelescope_factory
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: prop_api.proposalsettings.telescopeprojectid_factory
    :members:
    :undoc-members:
    :show-inheritance: