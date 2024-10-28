Nginx (Production Development)
==============================

This section is to be developed (TBD). It will cover the configuration and usage of Nginx in a production environment for the TraceT project.

Docker Configuration
--------------------

The nginx configuration file is located at ``./nginx/conf.d.ssl/default.conf``. Dockerfile is located at ``./nginx/Dockerfile``.

.. code-block:: Dockerfile

    FROM nginx:1.25

    RUN apt-get update && apt-get install -y procps

    RUN mkdir -p /home/app/staticfiles
    RUN mkdir -p /home/app/mediafiles
    RUN mkdir -p /home/app/certs


The following part will be added to the docker-compose file:

.. code-block:: docker-compose
    
  nginx:
    build: ./nginx
    container_name: nginx-container
    volumes:
      - ./nginx/conf.d.ssl/default.conf:/etc/nginx/conf.d/default.conf
      #- /etc/letsencrypt:/etc/letsencrypt
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
      - static_volume:/home/app/staticfiles
      - media_volume:/home/app/mediafiles
    ports:
      - 80:80
    depends_on:
      - web
    networks:
      - tracet-network

SSL Configuration
-----------------

letsencrypt is used to obtain and renew SSL certificates. The configuration files are located at ``./certbot/``.

Docker Compose file for SSL configuration is ``docker-compose.ssl.init.yml``. The following part will be added to the docker-compose file:

.. code-block:: ssl_init

  certbot:
    image: certbot/certbot
    container_name: certbot
    volumes:
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    command: certonly --webroot -w /var/www/certbot --force-renewal --email batbold.sanghi@gmail.com -d tracet.duckdns.org --agree-tos
    networks:
      - tracet-network

.. Every three months, the :

.. code-block:: bash

..   docker compose -f docker-compose.ssl.init.yml up certbot

Handling static files with Nginx
------------------------------

The static and media files are stored in the ``./static_volume`` and ``./media_volume`` directories. The both volumes are added to the ``web`` service and ``nginx`` service in the docker-compose file:

.. code-block:: nginx

    web:
        ...
        volumes:
        - .:/app
        - static_volume:/app/webapp_tracet/static_host
        - media_volume:/app/webapp_tracet/media
        - ./logs:/app/logs
        ...

    nginx:
        build: ./nginx
        container_name: nginx-container
        volumes:
        - ./nginx/conf.d.ssl/initial.conf:/etc/nginx/conf.d/default.conf
        - ./certbot/conf:/etc/letsencrypt
        - ./certbot/www:/var/www/certbot
        - static_volume:/home/app/staticfiles
        - media_volume:/home/app/mediafiles
        ports:
        - 80:80
        depends_on:
        - web
        networks:
        - tracet-network

Please check back later for updates on this section.
