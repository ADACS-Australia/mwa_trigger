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

   intro/what_is_tracet
   intro/overview_of_tracet


.. toctree::
   :maxdepth: 4
   :caption: Using TraceT:

   using_tracet/new_proposal
   using_tracet/new_user
   using_tracet/using_the_database

.. toctree::
   :maxdepth: 2
   :caption: Docker Scripts and Server Setup:

   docker_development/development_deployment
   docker_development/accessing_databases
   docker_development/nginx_production
   docker_development/restarting_nimbus

.. toctree::
   :maxdepth: 2
   :caption: Quick Start:

   quick_start/overview
   quick_start/creating_new_proposal
   quick_start/deleting_proposal


.. toctree::
   :maxdepth: 2
   :caption: Web App and Event Processing on Web App:

   web_application/web_database
   web_application/event_processing
   web_application/web_config


.. toctree::
   :maxdepth: 2
   :caption: Proposal API Overview:

   prop_api/prop_api_endpoints
   prop_api/prop_api_processing
   prop_api/prop_api_models
   prop_api/prop_api_factory

.. toctree::
   :maxdepth: 2
   :caption: Test API Overview:

   test_api/test_trigger_api

.. toctree::
   :maxdepth: 4
   :caption: Further Reading:

   further_reading/glossary
   further_reading/mwa_frequency_specifications
   further_reading/event_telescopes

