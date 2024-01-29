Running Server
==============

.. note:: The below assumes that you are running TraceT on Nimbus. Paths will need to be adjusted if you are running it elsewhere.

Checking for errors and inspecting logs
---------------------------------------
nginx errors are in

.. code-block::

   tail -f cat /var/log/nginx/error.log

All commands assume you're in the webapp_tracet sub directory. You can see the output of the server with

.. code-block::

   tail -f uwsgi-emperor.log

.. _start_server:

Starting the server
-------------------

Start the uwsgi server with

.. code-block::

   cd ~/tracet/webapp_tracet
   /home/ubuntu/.local/bin/uwsgi --ini webapp_tracet_uwsgi.ini

This will run in the background and the following sections describe how to restarting and stopping the server.

To capture events via the VOEvent network and kafka you need two background services to run.
We will run these in tmux so they persist through logout (and we can join/monitor them if we like).

.. code-block::
   
   cd ~/tracet/webapp_tracet
   tmux new -s kafka -d './kafka_daemon.sh'
   tmux new -s comet -d 'python3.10 twistd_comet_wrapper.py'

Restarting the server
---------------------
The web server will auto-restart if it crashes or is killed, so you can force a restart via:

.. code-block::

   kill -HUP `cat /tmp/project-master.pid`

The following script is a lot cleaner as it will stop and restart both the web server and the kafka/voevent listeners.

.. code-block::

   cd ~/tracet/
   ./restart-server.sh

Stopping the server
-------------------

.. code-block::

   /home/ubuntu/.local/bin/uwsgi --stop /tmp/project-master.pid


Installing updates
------------------

If the updates are small (no new dependencies or changes to database models), something as simple as the following will suffice:

.. code-block:: bash

   cd ~/tracet
   git pull
   kill -HUP `cat /tmp/project-master.pid`

If the update is larger then we have to bring everything down, pull changes, install requirements, migrate the database and then start it all up again:

.. code-block:: bash

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


All of the above is captured in the script `update-server.sh`, so you can run it via:

.. code-block:: bash

   cd ~/tracet
   ./update-server.sh



