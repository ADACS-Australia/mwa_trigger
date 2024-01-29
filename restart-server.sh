# check we are in /tracet
cd /home/ubuntu/tracet/webapp_tracet

# Stop servers
/home/ubuntu/.local/bin/uwsgi --stop /tmp/project-master.pid
tmux kill-server

# Start servers
/home/ubuntu/.local/bin/uwsgi --ini webapp_tracet_uwsgi.ini
tmux new -s kafka -d './kafka_daemon.sh'
tmux new -s comet -d 'python3.10 twistd_comet_wrapper.py'
