.. tracet documentation master file, created by
   sphinx-quickstart on Wed Feb  2 15:46:42 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to TraceT's documentation!
=======================================

This documentation is designed for users and developers of the TraceT web application.

Research users will find the first three sections most useful as it explains what TraceT is (Introduction), how to use it (Using TraceT) and the methods it uses (Trigger Logic)

Developers or administrators will find the following three sections more useful as it includes how to install and maintain the server (Web Application),
explanations of the software methodologies and layout (Developer Documentation) and the documentation of the TraceT python module (TraceT Package).


.. toctree::
   :maxdepth: 4
   :caption: Introduction:

   what_is_tracet
   overview_of_tracet


.. toctree::
   :maxdepth: 4
   :caption: Using TraceT:

   new_proposal
   new_user
   using_the_database


.. .. toctree::
..    :maxdepth: 4
..    :caption: Trigger Logic:

..    voevent_handling
..    grb


.. toctree::
   :maxdepth: 4
   :caption: Web Application:

   database_installation
   webapp_installation
   running_server
   restarting_nimbus


.. toctree::
   :maxdepth: 4
   :caption: Developer Documentation:

   developer_documentation
   git_hooks

.. toctree::
   :maxdepth: 1
   :caption: Proposal API Overview:

   prop_api_endpoints
   prop_api_processing
   prop_api_models
   prop_api_factory_classes


.. toctree::
   :maxdepth: 4
   :caption: Further Reading:

   glossary
   mwa_frequency_specifications
   event_telescopes