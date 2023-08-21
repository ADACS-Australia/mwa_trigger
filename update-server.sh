# check we are in /tracet
cd /home/ubuntu/tracet
# update git repo
git pull
# Stop server
/home/ubuntu/.local/bin/uwsgi --stop /tmp/project-master.pid

# Check for new dependent software
python3.10 -m pip install -r requirements.txt
python3.10 -m pip install .
python3.10 -m pip install -r webapp_tracet/requirements.txt

cd webapp_tracet

# Check for new static files
python3.10 manage.py collectstatic --noinput

# Make any required changes to the backend database
python3.10 manage.py makemigrations
python3.10 manage.py migrate

# Start server
/home/ubuntu/.local/bin/uwsgi --ini webapp_tracet_uwsgi.ini

# create environment variables required by kafka
tmux kill-server

# Reset comet and kafka event handlers
tmux new -s kafka -d './kafka_daemon.sh'
tmux new -s comet -d 'python3.10 twistd_comet_wrapper.py'