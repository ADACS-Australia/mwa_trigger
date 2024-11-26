#!/bin/bash
mkdir -p prop_api/logs

docker compose build 

sleep 2s
docker compose up -d 

sleep 15s

docker cp demo_trigger_db_updated.sql db-container:/

sleep 5s
docker exec -it db-container bash -c "PGPASSWORD=${POSTGRES_PASSWORD} psql -U trigger_admin -d trigger_db -f /demo_trigger_db_updated.sql"

sleep 5s
docker compose down

sleep 5s

docker compose up -d

docker exec -it api-container bash -c "DJANGO_SUPERUSER_USERNAME=${AUTH_USERNAME} DJANGO_SUPERUSER_EMAIL=${AUTH_USERNAME}@gmail.com DJANGO_SUPERUSER_PASSWORD=${AUTH_PASSWORD} python manage.py createsuperuser --noinput"

docker exec -it test-api-container bash -c "DJANGO_SUPERUSER_USERNAME=${AUTH_USERNAME} DJANGO_SUPERUSER_EMAIL=${AUTH_USERNAME}@gmail.com DJANGO_SUPERUSER_PASSWORD=${AUTH_PASSWORD} python manage.py createsuperuser --noinput"

# docker exec -it web-container bash -c "DJANGO_SUPERUSER_USERNAME=${AUTH_USERNAME} DJANGO_SUPERUSER_EMAIL=${AUTH_USERNAME}@gmail.com DJANGO_SUPERUSER_PASSWORD=${AUTH_PASSWORD} python manage.py createsuperuser --noinput"

echo "Deployment completed successfully."
