Accessing the Databases
=======================

Accessing the Database Inside the Docker Container
--------------------------------------------------

Checking current docker container, image, database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can delete the database volume and create a new one. Especially, you may need to do this when you want to reset the web application database. Please check the docker volume ls and delete the volume for the database:


.. code-block:: sh

   docker volume ls
   docker volume rm {volume_name}

You can also delete all docker images, containers, and system if you want to reset the whole docker environment:

Build docker
^^^^^^^^^^^^

First you need to run docker container:

.. code-block:: sh

   docker-compose down
   docker-compose build
   docker-compose up -d

Check Migrations for the web application:

.. code-block:: sh

   docker-compose exec web python3 webapp_tracet/manage.py makemigrations
   docker-compose exec web python3 webapp_tracet/manage.py migrate

For the api, you can restart the api container:

.. code-block:: sh

   docker-compose restart prop-api

You can also restart the django development container for the web application:

.. code-block:: sh

   docker-compose restart prop-api

Database
^^^^^^^^

Inside the Docker network, you can access the PostgreSQL database using the container name (db) as the host.

.. code-block:: sh

   docker exec -it <DB_container_NAME> psql -U <your_db_user> -d <your_db_name>

Example:

.. code-block:: sql

   $ psql -h localhost -U postgres -d trigger_db -p 5432
   Password for user postgres: 
   psql (14.12 (Ubuntu 14.12-0ubuntu0.22.04.1))
   Type "help" for help.

   trigger_db=# \dt

Accessing the Database from Outside the Docker Container
--------------------------------------------------------

Update docker-compose.yml
^^^^^^^^^^^^^^^^^^^^^^^^^

Add a `ports` section to the `db` service:

.. code-block:: yaml

   services:
     db:
       image: postgres:14
       ports:
         - "5432:5432"
       environment:
         POSTGRES_USER: your_db_user
         POSTGRES_PASSWORD: your_db_password
         POSTGRES_DB: your_db_name


Restart PostgreSQL Container:

.. code-block:: sh

   docker-compose restart db

Accessing PostgreSQL from Outside
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: sh

   psql -h localhost -U <your_db_user> -d <your_db_name> -p 5432

pgAdmin4
--------

1. Install pgAdmin4
2. Update docker-compose.yml
3. Configure pgAdmin4
4. Troubleshooting
5. View All Data in pgAdmin4
6. Run SQL Queries (Optional)

Potential Errors
----------------

1. Run migration
2. Errors with Users
3. Busy Port

For detailed instructions on each of these steps and how to handle potential errors, please refer to the full documentation.
