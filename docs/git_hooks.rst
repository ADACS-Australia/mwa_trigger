Setting up the pre-push hook for tests
==============

Install from requirements
---------------------------------------

.. code-block::

   pip install -r requirements.txt


Install pre-push hook
-------------------

.. code-block::

   pre-commit install --hook-type pre-push

Test pre-push hook
-------------------

.. code-block::

   pre-commit run --all-files



