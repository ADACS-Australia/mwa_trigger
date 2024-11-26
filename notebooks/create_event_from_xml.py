import os
import sys

import django
from dotenv import load_dotenv

# Load environment variables from the .env file
env_path = '/home/batbold/Projects/adacs_project_dev/TraceT/.env_web'  # Update this path to the location of your .env_api file
load_dotenv(env_path)
# Set the Django settings module environment variable
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webapp_tracet.settings')

# # Add the project root directory to the Python path
sys.path.append(
    '/home/batbold/Projects/adacs_project_dev/TraceT/webapp_tracet'
)  # Update this with the absolute path to your project root directory

# # Initialize Django
django.setup()

from trigger_app.models.event import Event, EventGroup

latestVoevent = Event.objects.get(pk=571218)

print(latestVoevent)
