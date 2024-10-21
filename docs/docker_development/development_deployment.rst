Development Deployment
======================

The development environment is a simplified version of the production environment and is intended to be run and accessed only from your local machine. This setup includes two primary containers: one for the Django web application and another for the PostgreSQL database.

Project Structure
-----------------

.. image:: ../figures/Architecture_dev.webp
   :alt: Architecture

Docker Containers
-----------------

- Web Container: Hosts the Django web application.
- Database Container: Runs PostgreSQL to manage the application's database.

Docker Configuration
--------------------

The Docker setup for TraceT includes the following key files:

- ``Dockerfile``: Defines the web container's build process.
- ``docker-compose.yml``: Manages multi-container Docker applications, including the web app and the database.

Dockerfile
^^^^^^^^^^

.. code-block:: dockerfile

   # Use an official Python runtime as a parent image
   FROM python:3.10-slim

   # Set the working directory in the container
   WORKDIR /app/webapp_tracet

   # Install git and PostgreSQL client development libraries
   RUN apt-get update && \
   apt-get install -y git && \
   apt-get install -y build-essential libpq-dev gcc

   # Copy requirements and install dependencies
   COPY requirements_dev.txt .
   RUN pip3 install --upgrade pip
   RUN pip3 install -r requirements_dev.txt

   # Install production dependencies
   COPY webapp_tracet/requirements.txt webapp_tracet/

   # Copy the additional requirements for the Django app
   RUN pip3 install -r webapp_tracet/requirements.txt

   # Set the PYTHONPATH environment variable
   ENV PYTHONPATH="/app:/app/webapp_tracet"

   CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]

docker-compose.yml
^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

   version: '3.8'

   services:
     db:
       image: postgres:14
       volumes:
         - postgres_data:/var/lib/postgresql/data
       environment:
         POSTGRES_USER: ${DB_USER}
         POSTGRES_PASSWORD: ${DB_PASSWORD}
         POSTGRES_DB: ${DB_NAME}
       networks:
         - tracet-network
       ports:
         - "5432:5432"
       env_file:
         - .env
       healthcheck:
         test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
         interval: 10s
         retries: 5
         start_period: 30s
         timeout: 5s

     web:
       build: .
       command: python manage.py runserver 0.0.0.0:8000
       volumes:
         - .:/app
         - static_volume:/app/webapp_tracet/static_host
         - media_volume:/app/webapp_tracet/media
       ports:
         - "8000:8000"
       env_file:
         - .env
       environment:
         - DB_SECRET_KEY=${DB_SECRET_KEY}
         - DJANGO_SETTINGS_MODULE=webapp_tracet.settings
         - DB_USER=${DB_USER}
         - DB_PASSWORD=${DB_PASSWORD}
         - DB_NAME=${DB_NAME}
         - DB_HOST=${DB_HOST}
         - DB_PORT=${DB_PORT}
       depends_on:
         db:
           condition: service_healthy
       networks:
         - tracet-network

   volumes:
     postgres_data:
     static_volume:
     media_volume:

   networks:
     tracet-network:
       driver: bridge

Advantages of Dockerization
---------------------------

Consistency Across Environments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Uniform Development and Production: Docker ensures that the application behaves the same way in development, testing, and production environments.
- Separate Containers: Each component (web app, database) runs in its own container, which isolates dependencies and avoids conflicts.
- Simplified Configuration: Docker Compose simplifies the process of configuring and starting multiple services with a single command.
- Cross-Platform Compatibility: Docker containers run consistently across different operating systems (Windows, Linux, macOS).
- Easy Scaling: Docker allows you to scale services up or down easily by modifying the Docker Compose configuration.
- Version Control: Docker images are versioned, making it easy to reproduce environments or roll back to previous versions.
- Resource Management: Docker containers share the host OS kernel, which makes them lightweight compared to virtual machines.

Running Docker on Different Platforms
-------------------------------------

- Windows: Use Docker Desktop for Windows. It provides an easy-to-use interface and integrates with WSL 2 for a more native Linux experience.
- Linux: Install Docker Engine and Docker Compose directly from your package manager. Follow the official Docker documentation for installation instructions.
- macOS: Use Docker Desktop for Mac. It includes a graphical interface and manages Docker containers with minimal setup.

Additional Features and Best Practices
--------------------------------------

- Health Checks: Implement health checks for your services to ensure they are running correctly.
- Backup Strategies: Plan and implement regular backups for your database data.
- Environment Variables: Use environment variables to manage configuration settings and secrets securely.
- Logging: Configure logging for both the web application and database to capture and analyze logs efficiently.
