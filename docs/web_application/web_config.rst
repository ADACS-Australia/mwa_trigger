Web Application Configuration and Installation
===============================================

Environment Variables
-------------------
The web application requires several environment variables to be set for proper operation:

.. csv-table::
   :header: "Variable","Description"

   "DB_USER","Postgres user name for database access"
   "DB_PASSWORD","Postgres password for database access"
   "DB_SECRET_KEY","Django secret key for security. Can be generated following `these instructions <https://saasitive.com/tutorial/generate-django-secret-key/>`_"
   "TWILIO_ACCOUNT_SID","Account SID from Twilio for SMS and call notifications"
   "TWILIO_AUTH_TOKEN","Authentication token from Twilio account"
   "TWILIO_PHONE_NUMBER","Twilio phone number used for sending notifications"
   "GMAIL_APP_PASSWORD","App password for the mwa.trigger@gmail.com email account"
   "MWA_SECURE_KEY","Project-specific secure key for MWA telescope scheduling"
   "ATCA_SECURE_KEY_FILE","Path to the secure key file for ATCA telescope scheduling"
   "SYSTEM_ENV","Set to 'PRODUCTION' for production environment (debug off, CSRF enabled) or 'DEVELOPMENT' for development"
   "UPLOAD_USER","Username for the account used by upload_xml.py for VOEvent uploads"
   "UPLOAD_PASSWORD","Password for the upload user account"




Docker Database Initialization
----------------------------
To initialize the database in Docker:

1. First, ensure the database container is running:

   .. code-block:: bash

      docker-compose up -d db

2. Create the database migrations:

   .. code-block:: bash

      docker-compose run web python manage.py makemigrations

3. Apply the migrations:

   .. code-block:: bash

      docker-compose run web python manage.py migrate

4. Create a superuser account:

   .. code-block:: bash

      docker-compose run web python manage.py createsuperuser

Web Application Setup
-------------------
To set up and run the web application:

1. Build the Docker images:

   .. code-block:: bash

      docker-compose build

2. Start all services:

   .. code-block:: bash

      docker-compose up -d

3. Verify the application is running:

   - Web interface should be available at ``http://localhost:8000``
   - Admin interface at ``http://localhost:8000/admin``

4. For development, you can view logs with:

   .. code-block:: bash

      docker-compose logs -f web



Django Settings for web application
----------------------------------

make sure the IP is in allowed hosts in settings.py and can make a request to api and test_trigger_api:

.. code-block::

    ALLOWED_HOSTS = [
        "127.0.0.1",
        "localhost",
        "www.mwa-trigger.duckdns.org",
        "mwa-trigger.duckdns.org",
        "www.tracet.duckdns.org",
        "tracet.duckdns.org",
        "146.118.70.58",
        "web",
        "prop-api",
        "test-api",
    ]

setup static files:

.. code-block::

    STATIC_URL = "/static/"
    STATICFILES_DIRS = (os.path.join(BASE_DIR, "static/"),)
    STATIC_ROOT = os.path.join(BASE_DIR, "static_host/")


The collection of statit files are defined in dockerfile when its used in production.

.. code-block::

    RUN if [ "$SYSTEM_ENV" = "PRODUCTION" ]; then \
        python manage.py collectstatic --noinput; \
    fi


Try a simple domain
-------------------
Grab a free subdomain from https://www.duckdns.org/domains that points to your ip then update the url in nginx's severname, and ALLOWED_HOSTS in settings.py

Getting a ssl certificate
-------------------------
Here are instructions on generating a ssl certificate

https://certbot.eff.org/instructions?ws=nginx&os=ubuntufocal


Troubleshooting
--------------
Common issues and solutions:

- If the database connection fails, ensure:
  - The ``DB_USER`` and ``DB_PASSWORD`` environment variables match your ``docker-compose.yml``
  - The database container is running (``docker-compose ps``)
  - The database has been properly initialized

- For permission issues:
  - Check that all environment variables are properly set
  - Verify the superuser account was created successfully
  - Ensure the upload user account exists and has correct permissions 