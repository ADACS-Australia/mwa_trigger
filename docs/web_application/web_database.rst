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
''''''''''''

* ``id`` - Primary key
* ``event_group_id`` - Foreign key to EventGroup model
* ``trig_id`` - Event trigger ID
* ``self_generated_trig_id`` - Boolean indicating if ID was self-generated
* ``telescope`` - Telescope identifier (e.g., SWIFT, Fermi)
* ``sequence_num`` - Sequence number
* ``event_type`` - Type of event (e.g., BAT_GRB_POS)
* ``topic`` - Event topic from kafka stream
* ``role`` - Event role
* ``duration`` - Event duration
* ``ra`` - Right Ascension (decimal degrees)
* ``dec`` - Declination (decimal degrees)
* ``ra_hms`` - Right Ascension (HMS format)
* ``dec_dms`` - Declination (DMS format)
* ``pos_error`` - Error radius in degrees
* ``recieved_data`` - Timestamp when event was received
* ``event_observed`` - Event observation timestamp
* ``xml_packet`` - XML packet data
* ``ignored`` - Boolean indicating if event is ignored
* ``source_name`` - Name of the source
* ``source_type`` - Event source type (e.g., GRB, GW)

Fermi-specific fields:

* ``fermi_most_likely_index`` - Most likely index for Fermi events
* ``fermi_detection_prob`` - Detection probability
* ``swift_rate_signif`` - Swift rate significance
* ``antares_ranking`` - ANTARES ranking
* ``hess_significance`` - HESS significance

LVC-specific fields:

* ``lvc_false_alarm_rate`` - False alarm rate for LVC events
* ``lvc_significant`` - Boolean indicating event significance
* ``lvc_event_url`` - Event URL
* ``lvc_binary_neutron_star_probability`` - BNS probability
* ``lvc_neutron_star_black_hole_probability`` - NSBH probability
* ``lvc_binary_black_hole_probability`` - BBH probability
* ``lvc_terrestial_probability`` - Terrestrial probability
* ``lvc_includes_neutron_star_probability`` - NS probability
* ``lvc_retraction_message`` - Retraction message if any
* ``lvc_skymap_fits`` - Path to FITS skymap
* ``lvc_prob_density_tile`` - Probability density per tile
* ``lvc_skymap_file`` - Uploaded skymap file
* ``lvc_instruments`` - Detecting instruments

EventGroup Model
'''''''''''''''''

* ``id`` - Primary key
* ``trig_id`` - Unique trigger identifier (max 64 chars)
* ``earliest_event_observed`` - Timestamp of first event observation
* ``latest_event_observed`` - Timestamp of most recent event observation
* ``ra`` - Right Ascension (decimal degrees)
* ``dec`` - Declination (decimal degrees)
* ``ra_hms`` - Right Ascension (HMS format)
* ``dec_dms`` - Declination (DMS format)
* ``pos_error`` - Position error radius in degrees
* ``recieved_data`` - Timestamp when data was received (auto-set)
* ``source_type`` - Event source type (3 chars, from SOURCE_CHOICES)
* ``ignored`` - Boolean flag for ignored events (default: True)
* ``event_observed`` - Event observation timestamp
* ``source_name`` - Name of the source (max 128 chars)

Telescope Model
'''''''''''''''
* ``name`` - Telescope name (e.g., MWA_VCS, MWA_correlate, ATCA)
* ``lon`` - Telescope longitude in degrees
* ``lat`` - Telescope latitude in degrees
* ``height`` - Telescope height above sea level in meters

EventTelescope Model
'''''''''''''''''''''
* ``name`` - Event Telescope name (e.g., SWIFT or Fermi)

TelescopeProjectID Model
'''''''''''''''''''''''''
* ``id`` - Primary key, Telescope Project ID for automatic scheduling
* ``password`` - Project password for telescope scheduling
* ``description`` - Brief project description
* ``atca_email`` - ATCA Proposal Email (required for ATCA authentication)
* ``telescope`` - Foreign key to Telescope model


ProposalSettings Model
'''''''''''''''''''''''

ProposalSettings table is shortened and only contains the basic project related information and the activation status of the proposal settings. Whenever docker starts, the table will be populated from proposalsettings_factory.py in proposalsettings module. The proposal_id is the unique identifier for the proposal settings and is updated whenever a new proposal settings is created. If deleted from the factory list, the proposalsettings is not active anymore and will not be used for triggering new proposals. However, the proposal_id will remain in the database and will be used for the old data.


* ``id`` - Primary key
* ``proposal_id`` - Unique proposal identifier (max 16 chars)
* ``telescope`` - Foreign key to Telescope model
* ``project_id`` - Foreign key to TelescopeProjectID model
* ``proposal_description`` - Brief proposal description (max 513 chars)
* ``priority`` - Proposal processing priority (lower is better, default: 1)
* ``event_telescope`` - Foreign key to EventTelescope model (optional)
* ``testing`` - Event trigger settings (from TRIGGER_ON choices)
* ``source_type`` - Source type to trigger on (from SOURCE_CHOICES)
* ``active`` - Boolean indicating if proposal is active (default: True)

ProposalDecision Model
'''''''''''''''''''''''
* ``id`` - Primary key
* ``decision`` - Decision status (Pending, Ignored, Error, Triggered, Canceled)
* ``decision_reason`` - Reason for decision (max 2056 chars)
* ``proposal`` - Foreign key to ProposalSettings
* ``event_group_id`` - Foreign key to EventGroup
* ``trig_id`` - Trigger identifier (max 64 chars)
* ``duration`` - Observation duration
* ``ra`` - Right Ascension (decimal degrees)
* ``dec`` - Declination (decimal degrees)
* ``alt`` - Altitude
* ``az`` - Azimuth
* ``ra_hms`` - Right Ascension (HMS format)
* ``dec_dms`` - Declination (DMS format)
* ``pos_error`` - Position error radius
* ``recieved_data`` - Timestamp when data was received (auto-set)

Observations Model
''''''''''''''''''
* ``trigger_id`` - Primary key, unique identifier for the observation (max 128 chars)
* ``telescope`` - Foreign key to Telescope model (references name field)
* ``proposal_decision_id`` - Foreign key to ProposalDecision model (optional)
* ``website_link`` - URL field for observation details (max 2028 chars)
* ``reason`` - Reason for observation (max 2029 chars, optional)
* ``mwa_sub_arrays`` - JSON field for MWA sub-array configuration (optional)
* ``created_at`` - Timestamp when observation was created (auto-set)
* ``request_sent_at`` - Timestamp when observation request was sent (optional)
* ``mwa_sky_map_pointings`` - Image field for MWA pointing map (optional)
* ``event`` - Foreign key to Event model (optional)
* ``mwa_response`` - JSON field for MWA response data (optional)

Database Relationships
''''''''''''''''''''''
* Event → TelescopeObservation (one-to-many)
* Event → UserAlerts (one-to-many)
* ProposalSettings → TelescopeObservation (one-to-many)
* User → UserProfile (one-to-one)
* TelescopeObservation → ObservationLog (one-to-many)
* EventGroup → Event (one-to-many, via event_group_id with related_name="voevent")
* TelescopeProjectID → Telescope (many-to-one)
* ProposalSettings → Telescope (many-to-one)
* ProposalSettings → TelescopeProjectID (many-to-one)
* ProposalSettings → EventTelescope (many-to-one)
* ProposalDecision → ProposalSettings (many-to-one)
* ProposalDecision → EventGroup (many-to-one)
* Observations → Telescope (many-to-one)
* Observations → ProposalDecision (many-to-one)
* Observations → Event (many-to-one)




