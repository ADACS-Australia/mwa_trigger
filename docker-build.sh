#!/bin/bash
mkdir -p prop_api/logs

docker-compose build 

sleep 2s
docker-compose up -d 

sleep 15s

docker cp demo_trigger_db.sql db-container:/

sleep 5s
docker exec -it db-container bash -c "PGPASSWORD=${POSTGRES_PASSWORD} psql -U trigger_admin -d trigger_db -f /demo_trigger_db.sql"

sleep 5s
docker-compose down

sleep 5s

docker-compose up -d

echo "Deployment completed successfully."
