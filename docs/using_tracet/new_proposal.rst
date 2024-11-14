.. _proposals:

Working with a Proposal
=======================

The proposal api is designed to handle several science
cases using several telescopes at once through "proposals". Your project
may have several proposals. For example, if you want to observe GRBs from
SWIFT with the MWA and ATCA, you will need to make two proposals. One
observes GRBs from SWIFT with the MWA, and another observes GRBs with ATCA.


Step 1: Creating the Proposal
-----------------------------

please refer to the :ref:`Creating New Proposal <creating_new_proposal>` for the details.

Step 2: Update Alert Permissions
--------------------------------
By default, all users will have permission to receive trigger alerts and
will not have permission to receive pending and debug alerts for all
proposals. As an admin, you can give users you trust permission to receive debug
and pending alerts and decide if a VOEvent should be triggered on or not. Use the
`Alert Pemission <https://tracet.duckdns.org/admin/trigger_app/alertpermission/>`_
page to edit these permissions.

Step 3: Notify Users to Update their Alerts
-------------------------------------------
All users have proposal specific alert settings, so to receive an alert for
your proposal, all users must update their alerts on the
`User Alert Control  <https://tracet.duckdns.org/user_alert_status/>`_ page.
Users can set multiple alert types per proposal (e.g. email and SMS) and
per alert type (trigger, pending and debug).
It is recommended that users set a phone call alert type for pending alerts
to assure the pending decision is promptly investigated.



