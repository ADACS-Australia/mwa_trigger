Web Application & Database
=========================

Overview
--------
The web application is built with Django and uses PostgreSQL for data storage. It serves as the primary interface for users to interact with the system.

Components
----------

Django Web Application
~~~~~~~~~~~~~~~~~~~~
* Single app called ``trigger_app``
* Handles user authentication and authorization
* Manages event processing and telescope triggers

Database Structure
~~~~~~~~~~~~~~~~~
* PostgreSQL database
* Key models:
    * Event
    * UserAlerts
    * ProposalSettings

Event Processing
---------------

Event Input
~~~~~~~~~~
* Uses twistd_comet_wrapper.py for event listening
* Processes VOEvents through upload_xml.py
* Events are parsed and stored in the Event model

Event Handling
~~~~~~~~~~~~~
* Triggered through signals (trigger_app/signals.py)
* Groups events by trig_id
* Processes events against ProposalSettings
* Triggers observations via telescope_observe.py

Configuration
------------
[Configuration details for web application]

Installation
-----------
[Installation steps] 