Test Trigger API
===============

Overview
--------
The Test Trigger API provides testing for the telescope proposal requests and mock responses from the atca and mwa api.

API Endpoints
------------
The following endpoints are available in the Test Trigger API:

/atca_proposal_request/
~~~~~~~~~~~~~~~~~~~~~~
**POST** - Submit an ATCA proposal request

* Parameters:
    * authToken (str): Authentication token
    * email (str): User email
    * test (bool): Test mode flag
    * noTimeLimit (bool): Time limit override flag
    * noScoreLimit (bool): Score limit override flag
    * request (json): Proposal request details

/mwa_proposal_request/triggerbuffer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**POST** - Submit an MWA proposal request for trigger buffer

* Query Parameters:
    * project_id (str): Project identifier

* Form Data:
    * secure_key (str): Security key
    * pretend (bool): Pretend/simulation mode
    * start_time (int): Start time for the observation
    * obstime (int): Observation duration

/mwa_proposal_request/triggervcs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**POST** - Submit an MWA proposal request for trigger VCS

* Query Parameters:
    * project_id (str): Project identifier
    * obsname (str): Observation name

* Form Data: Various MWA-specific parameters

Mock Data
--------
The Test Trigger API provides default mock responses for testing telescope proposal requests:

ATCA Mock Response
~~~~~~~~~~~~~~~~~
Default ATCA response includes:

* Authentication validation
* Project details (code C3204)
* Schedule information with target coordinates
* Observation parameters (duration, dates)
* Test mode settings

MWA Mock Response
~~~~~~~~~~~~~~~~
Default MWA response includes:

* Schedule commands and execution status
* Observation parameters
    * Multiple subarrays (NE, NW, SE, SW)
    * Coordinates for each subarray
    * Frequency specifications
    * Project details (G0094)
* Trigger ID and success status

These mock responses can be used for:
* Event simulation
* Proposal simulation
* Response validation

Configuration
------------
[Configuration details for test API]

Installation
-----------
[Installation steps] 