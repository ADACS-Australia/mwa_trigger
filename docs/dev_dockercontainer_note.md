# Table of Contents
- [Development Deployment](#development-deployment)
  - [Project Structure](#project-structure)
  - [Docker Containers](#docker-containers)
  - [External Tools](#external-tools)
  - [Docker Configuration](#docker-configuration)
    - [Dockerfile](#dockerfile)
    - [Docker-compose.yml](#docker-composeyml)
  - [Advantages of Dockerization](#advantages-of-dockerization)
    - [Consistency Across Environments](#consistency-across-environments) 
  - [Running Docker on Different Platforms](#running-docker-on-different-platforms)
  - [Additional Features and Best Practices](#additional-features-and-best-practices)
- [Accessing the Database Inside the Docker Container](#accessing-the-database-inside-the-docker-container)
   - [Checking Current Docker Container, Image, Database](#checking-current-docker-container-image-database)
   - [Build Docker](#build-docker)
     - [Check Migrations](#check-migrations)
     - [Create Migrations](#create-migrations)
     - [Apply Migrations](#apply-migrations)
     - [Start Django Development Server](#start-django-development-server)
   - [Database](#database)
   - [Example](#example)
- [Accessing the Database from Outside the Docker Container](#accessing-the-database-from-outside-the-docker-container)
   - [Update docker-compose.yml](#update-docker-composeyml)
   - [Update settings.py](#update-settingspy)
   - [Configure PostgreSQL to Accept Remote Connections](#configure-postgresql-to-accept-remote-connections)
     - [postgresql.conf](#postgresqlconf)
     - [pg_hba.conf](#pg_hbaconf)
   - [Restart PostgreSQL Container](#restart-postgresql-container)
- [Accessing PostgreSQL from Outside](#accessing-postgresql-from-outside)
   - [Example docker-compose.yml](#example-docker-composeyml)
- [pgAdmin4](#pgadmin4)
   - [Install pgAdmin4](#install-pgadmin4)
   - [Update docker-compose.yml](#update-docker-composeyml)
   - [Configure pgAdmin4](#configure-pgadmin4)
   - [Troubleshooting](#troubleshooting)
   - [View All Data in pgAdmin4](#view-all-data-in-pgadmin4)
   - [Run SQL Queries (Optional)](#run-sql-queries-optional)
- [Potential Errors](#potential-errors)
- [Nginx](#nginx)
- [References](#references)

# Development deployment
The development environment is a simplified version of the production environment and is intended to be run and accessed only from your local machine. This setup includes two primary containers: one for the Django web application and another for the PostgreSQL database. Additionally, PostgreSQL data can be accessed using pgAdmin4, running outside the Docker containers.

## Project Structure
![Architecture](figures/Architecture_dev.webp)

## Docker Containers
- Web Container: Hosts the Django web application.
- Database Container: Runs PostgreSQL to manage the application's database.
## External Tools

pgAdmin4: Provides a web-based interface to interact with the PostgreSQL database.
## Docker Configuration
The Docker setup for TraceT includes the following key files:

- `Dockerfile`: Defines the web container's build process.
- `docker-compose.yml`: Manages multi-container Docker applications, including the web app and the database.

### Dockerfile
```dockerfile
# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

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

CMD ["python3", "webapp_tracet/manage.py", "runserver", "0.0.0.0:8000"] 
```

### docker-compose.yml
```yaml
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
    command: python webapp_tracet/manage.py runserver 0.0.0.0:8000
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

```

## Advantages of Dockerization
### Consistency Across Environments
Uniform Development and Production: Docker ensures that the application behaves the same way in development, testing, and production environments. This consistency reduces "works on my machine" issues.
- Separate Containers: Each component (web app, database) runs in its own container, which isolates dependencies and avoids conflicts.
- Simplified Configuration: Docker Compose simplifies the process of configuring and starting multiple services with a single command.
- Cross-Platform Compatibility: Docker containers run consistently across different operating systems (Windows, Linux, macOS). Developers can work in their native environment without worrying about compatibility issues.
- Easy Scaling: Docker allows you to scale services up or down easily by modifying the Docker Compose configuration.
- Version Control: Docker images are versioned, making it easy to reproduce environments or roll back to previous versions.
- Resource Management: Docker containers share the host OS kernel, which makes them lightweight compared to virtual machines.

## Running Docker on Different Platforms
- Windows: Use Docker Desktop for Windows. It provides an easy-to-use interface and integrates with WSL 2 for a more native Linux experience.
- Linux: Install Docker Engine and Docker Compose directly from your package manager. Follow the official Docker documentation for installation instructions.
- macOS: Use Docker Desktop for Mac. It includes a graphical interface and manages Docker containers with minimal setup.

## Additional Features and Best Practices
- Health Checks: Implement health checks for your services to ensure they are running correctly.
- Backup Strategies: Plan and implement regular backups for your database data.
- Environment Variables: Use environment variables to manage configuration settings and secrets securely.
- Logging: Configure logging for both the web application and database to capture and analyze logs efficiently.

By leveraging Docker for the TraceT project, you streamline development, ensure consistency across environments, and facilitate easier deployment and scaling. Docker provides a robust solution for managing complex applications with multiple dependencies.


# Accessing the Database Inside the Docker Container
## Checking current docker container, image, database
#### Delete all docker volumes
```sh
docker volume ls
```
remove all
```sh
docker volume rm $(docker volume ls -q)
```
If you want to force remove all unused volumes:
```sh
docker volume prune
```

#### Delete all docker images
```sh
docker rmi $(docker images -q)
```
To remove all stopped containers:
```sh
docker container prune
```
You can also combine the removal of all containers, volumes, and networks if necessary:
```sh
docker system prune -a
```

## Build docker
First you need to run docker container

```sh
docker-compose down
docker-compose --build
docker-compose up
```
At the beginning, you may get the error message indicates that the `trigger_app_status` table does not exist in your PostgreSQL database.

- Check Migrations: Ensure that all migrations for your Django app have been created and applied.
- Create Migrations: If the migrations haven't been created, you can create them using the makemigrations command.
  ```sh
  docker-compose exec web python3 webapp_tracet/manage.py makemigrations
  ```
- Apply Migrations: Apply the migrations to the database.
  ```sh
  docker-compose exec web python3 webapp_tracet/manage.py migrate
  ```
Then you can check the containers
```sh
docker ps
```
Or check the Database
```sh
docker-compose exec db psql -U postgres -d <your_database_name> -c '\dt'
```
Start Django Development Server:

```sh
docker-compose exec web python3 manage.py runserver 0.0.0.0:8000
```

Then you can access the web browser at `http://localhost:8000/` or `http://127.0.0.1:8000/`

## Database
Inside the Docker network, you can access the PostgreSQL database using the container name (db) as the host. 

In the current `settings.py` correctly specifies the `DB_HOST` as `db`, which matches the service name in the `docker-compose.yml`.

You can use docker exec to start a shell session inside the PostgreSQL container and then use `psql` to interact with the database.

```sh
$ docker exec -it <DB_container_NAME> psql -U <your_db_user> -d <your_db_name>
```
Replace `<DB_container_NAME>`, `<your_db_user>` and `<your_db_name>` with your actual database container name, database `username` and `name`.

Check the docker container to see the container of database
```sh
$ docker ps
CONTAINER ID   IMAGE         COMMAND                  CREATED          STATUS                    PORTS                                       NAMES
79350288485a   tracet-web    "python manage.py ru…"   43 seconds ago   Up 36 seconds             0.0.0.0:8000->8000/tcp, :::8000->8000/tcp   tracet-web-1
602c31367475   postgres:14   "docker-entrypoint.s…"   43 seconds ago   Up 42 seconds (healthy)   0.0.0.0:5432->5432/tcp, :::5432->5432/tcp   tracet-db-1
```

For example with `.env`
```
DB_USER=postgres
DB_PASSWORD=postgres
DB_SECRET_KEY=tracet12345
DB_NAME=trigger_db
DB_HOST=db
DB_PORT=5432
```
Use the following command to access the PostgreSQL database from your host machine:

```sh
$ docker exec -it tracet-db-1 psql -U postgres -d trigger_db
psql (14.12 (Debian 14.12-1.pgdg120+1))
Type "help" for help.

trigger_db=#
```

#### Example

```sql
$ psql -h localhost -U postgres -d trigger_db -p 5432
Password for user postgres: 
psql (14.12 (Ubuntu 14.12-0ubuntu0.22.04.1))
Type "help" for help.

trigger_db=# \dt
                         List of relations
 Schema |                 Name                  | Type  |  Owner   
--------+---------------------------------------+-------+----------
 public | auth_group                            | table | postgres
 public | auth_group_permissions                | table | postgres
 public | auth_permission                       | table | postgres
 public | auth_user                             | table | postgres
 public | auth_user_groups                      | table | postgres
 public | auth_user_user_permissions            | table | postgres
 public | django_admin_log                      | table | postgres
 public | django_apscheduler_djangojob          | table | postgres
 public | django_apscheduler_djangojobexecution | table | postgres
 public | django_content_type                   | table | postgres
 public | django_migrations                     | table | postgres
 public | django_session                        | table | postgres
 public | trigger_app_alertpermission           | table | postgres
 public | trigger_app_atcauser                  | table | postgres
 public | trigger_app_cometlog                  | table | postgres
 public | trigger_app_event                     | table | postgres
 public | trigger_app_eventgroup                | table | postgres
 public | trigger_app_eventtelescope            | table | postgres
 public | trigger_app_observations              | table | postgres
 public | trigger_app_proposaldecision          | table | postgres
 public | trigger_app_proposalsettings          | table | postgres
 public | trigger_app_status                    | table | postgres
 public | trigger_app_telescope                 | table | postgres
 public | trigger_app_telescopeprojectid        | table | postgres
 public | trigger_app_useralerts                | table | postgres
(25 rows)
```
- To list all column names for the `trigger_app_observations` table,
```sql
trigger_db=# SELECT column_name
trigger_db-# FROM information_schema.columns
trigger_db-# WHERE table_name = 'trigger_app_observations';
       column_name       
-------------------------
 mwa_sub_arrays
 mwa_response
 event_id
 proposal_decision_id_id
 created_at
 request_sent_at
 telescope_id
 website_link
 reason
 mwa_sky_map_pointings
 trigger_id
(11 rows)
```
# Accessing the Database from Outside the Docker Container
To access the database from outside the Docker container (e.g., from your host machine or another machine), you need to expose the PostgreSQL port and ensure your database is configured to accept external connections.

### Update docker-compose.yml:
Add a `ports` section to the `db` service that your PostgreSQL service in `docker-compose.yml` exposes the port 5432.

Update `docker-compose.yml`:
```yaml
services:
  db:
    image: postgres:14
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: your_db_user
      POSTGRES_PASSWORD: your_db_password
      POSTGRES_DB: your_db_name
```
### Update settings.py
Since your `settings.py` already uses environment variables for database configuration, no changes are needed for accessing the database from within the Docker network. However, to access the database from outside the Docker container, you should ensure the environment variables are set correctly.

Ensure you have the following `environment variables` set correctly when running Docker:
```
DB_USER
DB_PASSWORD
DB_NAME
DB_HOST (set to localhost for external access)
DB_PORT (set to 5432)
```
### Configure PostgreSQL to Accept Remote Connections:
You need to update the postgresql.conf and pg_hba.conf to allow connections from outside.

#### postgresql.conf:
Find the `listen_addresses` setting and set it to `'*'` to allow connections from any IP address.

```plaintext
listen_addresses = '*'
```
This file is usually located in `/var/lib/postgresql/data` or `/var/lib/postgresql/data/postgresql.conf` inside the container. You can access it by starting a shell session in the container:

```sh
$ docker exec -it tracet-db-1 bash
```

Then, open the file with a text editor like nano or vim:

```sh
$ nano /var/lib/postgresql/data/postgresql.conf
```

#### pg_hba.conf:
Add a line to allow connections from your host machine's IP address. This file is also usually located in `/var/lib/postgresql/data` or `/var/lib/postgresql/data/pg_hba.conf`.

```plaintext
host    all             all             0.0.0.0/0               md5
```

This configuration allows any IP address to connect to the database using MD5 password authentication. You can restrict it to specific IP addresses for better security.

### Restart PostgreSQL Container:
After making these changes, restart your PostgreSQL container to apply the new settings.

```sh
$ docker-compose restart db
```

## Accessing PostgreSQL from Outside
Once you've updated your docker-compose.yml and PostgreSQL configuration, you can connect to the database from your host machine using a tool like psql or any PostgreSQL client (e.g., pgAdmin, DBeaver).

```sh
$ psql -h localhost -U <your_db_user> -d <your_db_name> -p 5432
```
Replace `localhost` with your Docker host `IP address` if you're accessing it from another machine.

##### For example with previous `.env`:

Use the following command to access the PostgreSQL database from your host machine:

```sh
$ psql -h localhost -U postgres -d trigger_db -p 5432
Password for user postgres: 
psql (14.12 (Ubuntu 14.12-0ubuntu0.22.04.1))
Type "help" for help.

trigger_db=# \dt
```
- `-h` `localhost` specifies the host.
- `-U` `postgres` specifies the username.
- `-d` `trigger_db` specifies the database name.
- `-p` `5432` specifies the port.

#### Example docker-compose.yml
Here’s an example of a complete docker-compose.yml with the necessary changes:

```yaml
version: '3.8'

services:
  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/code
    ports:
      - "8000:8000"
    depends_on:
      - db

  db:
    image: postgres:14
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: your_db_user
      POSTGRES_PASSWORD: your_db_password
      POSTGRES_DB: your_db_name
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## pgAdmin4

To access your PostgreSQL database inside a Docker container using pgAdmin4 from your local machine, follow these steps:

### 1. Install pgAdmin4
If you don't already have pgAdmin4 installed on your local machine, download and install it from pgAdmin's official site.

### 2. Update docker-compose.yml
Ensure that your docker-compose.yml exposes the PostgreSQL port to the host machine. Based on your setup, you should have this already:

```yaml
ports:
  - "5432:5432"
```
### 3. Configure pgAdmin4
- Open pgAdmin4: Launch pgAdmin4 from your local machine.
- Add a New Server in pgAdmin4:
    - Open pgAdmin4 and right-click on "Servers" in the left sidebar.
    - Select "Create" -> "Server...".
- Configure the Connection:
    - General Tab:
        - Name: Enter a name for your server connection (e.g., Tracet PostgreSQL).
    - Connection Tab:
        - `Host name/address`: `localhost` (since PostgreSQL is exposed on port 5432 of your local machine).
        - `Port`: `5432` (the port mapped in your docker-compose.yml).
        - `Maintenance database`: `trigger_db` (the name of the database you want to connect to).
        - `Username`: `postgres` (the user configured in your .env file).
        - `Password`: `postgres` (the password configured in your .env file).
- Save the Configuration: Click "Save" to establish the connection.

### 4. Troubleshooting
If you encounter issues:

- Ensure PostgreSQL Container is Running:
Verify that your PostgreSQL container is running and healthy:

```sh
docker ps
```
- Check Port Binding:
Ensure no other process is using port 5432 on your local machine. You can check for conflicts with:

```sh
sudo lsof -i :5432
```
- Verify Docker Logs:
Check Docker logs for any issues related to PostgreSQL:

```sh
docker logs tracet-db-1
```
- Restart Docker Services:
Sometimes, restarting Docker services can resolve connection issues:

```sh
docker-compose down
docker-compose up -d
```

### 5. To view all the data in pgAdmin4

#### Open pgAdmin4 and Connect to Your Server:
- Launch pgAdmin4.
- In the "Browser" panel on the left, expand the server group and select your server connection (e.g., `Tracet PostgreSQL`).

#### Navigate to the Database:
- Expand the server node, and then expand the Databases node.
- Click on the database you want to inspect (e.g., `trigger_db`).

#### View Tables and Data:
- Expand the `Schemas` node under your database.
- Expand the `public schema` (or the schema where your tables are located).
- Click on the Tables node to see a list of tables in the selected schema.
#### View Table Data:

- Right-click on the table you want to view and select `View/Edit Data > All Rows`. Alternatively, you can also select `View Data > First 100 Rows` if you only want to view a subset of data.
- A new tab will open showing the table data in a grid format. You can scroll through the data, and use the built-in search and filter functionalities to find specific records.

#### Run SQL Queries (Optional):
- If you want to execute custom SQL queries to view data, you can use the `Query Tool`.
- Right-click on your database and select `Query Tool`.
- Enter your SQL query in the editor (e.g., SELECT * FROM your_table;).
- Click the Execute button (or press F5) to run the query and see the results in the output panel.

##### For example:
- I created a user `root` and email `ngoctam.lam@curtin.edu.au` with `python3 manage.py createsuperuser` to login in web browser.
- Within the `Query Tool`, to view all records from the auth_user table:
    ```sql
    SELECT * FROM auth_user;
    ```
- To view specific columns from a table, specify the columns in the SELECT query. For example, to view the `username` and `email` columns from the `auth_user` table:
    ```sql
    SELECT username, email FROM auth_user;
    ```
- The data output will be `username`: `root` and `email`: `ngoctam.lam@curtin.edu.au`.

##### Another example:
- To list all column names for the `trigger_app_observations` table, use the following SQL query:
    ```sql
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'trigger_app_observations';
    ```
- It will list all information which is same at the models.py
    ```py
    class Observations(models.Model):
        trigger_id = models.CharField(max_length=128, primary_key=True)
        telescope = models.ForeignKey(
            Telescope,
            to_field="name",
            verbose_name="Telescope name",
            on_delete=models.CASCADE,
        )
        proposal_decision_id = models.ForeignKey(
            ProposalDecision, on_delete=models.SET_NULL, blank=True, null=True
        )
        website_link = models.URLField(max_length=2028)
        reason = models.CharField(max_length=2029, blank=True, null=True)
        mwa_sub_arrays = models.JSONField(null=True)
        created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
        request_sent_at = models.DateTimeField(blank=True, null=True)
        mwa_sky_map_pointings = models.ImageField(
            upload_to="mwa_pointings", blank=True, null=True
        )
        event = models.ForeignKey(Event, on_delete=models.SET_NULL, blank=True, null=True)
        mwa_response = models.JSONField(blank=True, null=True)
    ```


# Potential Errors

## 1. Run migration

At the beginning you should do
```sh
docker-compose exec web python3 manage.py migrate
```
This command applies all migrations, creating tables and updating the database schema as needed.

If this is the first time you’re setting up the database or if you’ve recreated it, ensure that your initial data and schema are properly set up:

Create Superuser (if necessary):

```sh
docker-compose exec web python manage.py createsuperuser
```
## 2. Errors with Users
- Check the docker container
```sh
$ docker ps
CONTAINER ID   IMAGE         COMMAND                  CREATED       STATUS                 PORTS                                       NAMES
22ec8a0fa989   tracet-web    "python manage.py ru…"   2 hours ago   Up 2 hours             0.0.0.0:8000->8000/tcp, :::8000->8000/tcp   tracet-web-1
58d6e894efb5   postgres:14   "docker-entrypoint.s…"   2 hours ago   Up 2 hours (healthy)   0.0.0.0:5432->5432/tcp, :::5432->5432/tcp   tracet-db-1
$ docker exec -it tracet-db-1 psql -U postgres
psql (14.12 (Debian 14.12-1.pgdg120+1))
Type "help" for help.
postgres=# 
```
- Creating a new USER_NAME
```postgres
postgres=# \du
                                   List of roles
 Role name |                         Attributes                         | Member of 
-----------+------------------------------------------------------------+-----------
 postgres  | Superuser, Create role, Create DB, Replication, Bypass RLS | {}

postgres=# CREATE USER <USER_NAME> WITH PASSWORD '<USER_NAME>';
CREATE ROLE
postgres=# ALTER USER <USER_NAME> CREATEDB;
ALTER ROLE
postgres=# \du
                                     List of roles
  Role name   |                         Attributes                         | Member of 
--------------+------------------------------------------------------------+-----------
 postgres     | Superuser, Create role, Create DB, Replication, Bypass RLS | {}
 <USER_NAME>  | Create DB                                                  | {}

postgres=# 
```
## 3. Busy Port

#### Check if port 5432 is occupied by another service on your host machine
```sh
sudo lsof -i :5432
```
- This will show any services listening on port 5432. If there’s no output, the port is free.
- If it shows as below means the port is being used:
```sh
$ sudo lsof -i :5432
COMMAND   PID     USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
postgres 8620 postgres    5u  IPv4  55880      0t0  TCP localhost:postgresql (LISTEN)
  ```
- Stop the Existing PostgreSQL Service: If you want to use port 5432 for your Docker container, you'll need to stop the existing PostgreSQL service. You can do this by stopping the PostgreSQL service on your host machine:

On Linux/Ubuntu:

```sh
sudo systemctl stop postgresql
```
# Nginx
TBD

# References
- [Dockerizing Django with Postgres, Gunicorn, and Nginx](https://testdriven.io/blog/dockerizing-django-with-postgres-gunicorn-and-nginx/#static-files)