.. _deleting_proposal:

Deleting Proposal
=================

Deleting Proposal Settings Model
------------------------------

By just removing the proposal settings model from the factory class, the proposal settings model is no longer available for the proposal api.
After the proposal settings model is deleted from the factory class, the ``update button`` needs to be clicked to update the web application database. Once the web application database is updated, 
the deleted proposal settings model gets inactive status in the database. It means that the deleted proposal settings model is not used anymore in creating new proposals.
However, it is still used in the web appication since it may be used in the existing proposal decisions. If the deleted proposal settings model is not used in the existing proposal decisions, 
it can be deleted manually from the database using Django admin interface. 
