Web Application & Database
==========================

Overview
--------
The web application is built with Django and uses PostgreSQL for data storage. It serves as the primary interface for users to interact with the system.

Components
----------

Django Web Application
~~~~~~~~~~~~~~~~~~~~~~

* Single app called ``trigger_app``
* Handles user authentication and authorization
* Manages event processing and telescope triggers

Database Structure
~~~~~~~~~~~~~~~~~~
* PostgreSQL database
* Tables are managed through Django's ORM
* Key models and their fields:

Event Model
''''''''''
* ``id`` - Primary key
* ``trig_id`` - Event trigger ID
* ``event_type`` - Type of event (e.g., GRB, GW)
* ``time_received`` - Timestamp when event was received
* ``time_created`` - Event creation timestamp
* ``ra`` - Right Ascension
* ``dec`` - Declination
* ``error_radius`` - Error radius in degrees
* ``xml_file`` - Path to stored XML file
* ``processed`` - Boolean indicating processing status
* ``status`` - Current event status
* ``importance`` - Event importance score
* ``source`` - Event source (e.g., SWIFT, FERMI)

UserAlerts Model
'''''''''''''''
* ``id`` - Primary key
* ``user`` - ForeignKey to Django User model
* ``event`` - ForeignKey to Event model
* ``alert_type`` - Type of alert
* ``timestamp`` - Alert creation time
* ``read`` - Boolean indicating if alert was read
* ``email_sent`` - Boolean indicating if email was sent

ProposalSettings Model
'''''''''''''''''''''
* ``id`` - Primary key
* ``name`` - Proposal name
* ``pi`` - Principal Investigator name
* ``active`` - Boolean indicating if proposal is active
* ``start_date`` - Proposal start date
* ``end_date`` - Proposal end date
* ``observation_type`` - Type of observation
* ``priority`` - Proposal priority level
* ``min_importance`` - Minimum event importance threshold
* ``max_importance`` - Maximum event importance threshold

TelescopeObservation Model
'''''''''''''''''''''''''
* ``id`` - Primary key
* ``event`` - ForeignKey to Event model
* ``telescope`` - Telescope identifier
* ``status`` - Observation status
* ``time_submitted`` - Submission timestamp
* ``time_completed`` - Completion timestamp
* ``exposure_time`` - Requested exposure time
* ``filters`` - Observation filters
* ``proposal`` - ForeignKey to ProposalSettings

UserProfile Model
'''''''''''''''
* ``id`` - Primary key
* ``user`` - OneToOne relation to Django User model
* ``institution`` - User's institution
* ``role`` - User role (e.g., PI, Co-I)
* ``notification_preferences`` - JSON field for notification settings

TelescopeStatus Model
''''''''''''''''''''
* ``id`` - Primary key
* ``telescope`` - Telescope identifier
* ``status`` - Current operational status
* ``last_updated`` - Last status update time
* ``weather_conditions`` - Current weather conditions
* ``technical_state`` - Technical status details

ObservationLog Model
'''''''''''''''''''
* ``id`` - Primary key
* ``observation`` - ForeignKey to TelescopeObservation
* ``timestamp`` - Log entry time
* ``message`` - Log message
* ``level`` - Log level (INFO, WARNING, ERROR)
* ``source`` - Log source component

Database Relationships
''''''''''''''''''''
* Event → TelescopeObservation (one-to-many)
* Event → UserAlerts (one-to-many)
* ProposalSettings → TelescopeObservation (one-to-many)
* User → UserProfile (one-to-one)
* TelescopeObservation → ObservationLog (one-to-many) 



