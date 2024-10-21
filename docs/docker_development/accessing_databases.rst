Accessing the Databases
=======================

Accessing the Database Inside the Docker Container
--------------------------------------------------

Checking current docker container, image, database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Delete all docker volumes:

.. code-block:: sh

   docker volume ls
   docker volume rm $(docker volume ls -q)
   docker volume prune

Delete all docker images:

.. code-block:: sh

   docker rmi $(docker images -q)
   docker container prune
   docker system prune -a

Build docker
^^^^^^^^^^^^

First you need to run docker container:

.. code-block:: sh

   docker-compose down
   docker-compose --build
   docker-compose up

Check Migrations:

.. code-block:: sh

   docker-compose exec web python3 webapp_tracet/manage.py makemigrations
   docker-compose exec web python3 webapp_tracet/manage.py migrate

Start Django Development Server:

.. code-block:: sh

   docker-compose exec web python3 manage.py runserver 0.0.0.0:8000

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

Update settings.py
^^^^^^^^^^^^^^^^^^

Ensure you have the following environment variables set correctly when running Docker:

.. code-block:: plaintext

   DB_USER
   DB_PASSWORD
   DB_NAME
   DB_HOST (set to localhost for external access)
   DB_PORT (set to 5432)

Configure PostgreSQL to Accept Remote Connections
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Update `postgresql.conf`:

.. code-block:: plaintext

   listen_addresses = '*'

Update `pg_hba.conf`:

.. code-block:: plaintext

   host    all             all             0.0.0.0/0               md5

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
