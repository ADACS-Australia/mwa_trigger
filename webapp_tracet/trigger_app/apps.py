import sys

from django.apps import AppConfig
from django.conf import settings


class TriggerAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "trigger_app"

    def ready(self):
        import trigger_app.signals
        from trigger_app.utils.utils_api import init_session

        # initialize session
        init_session()

        # Initialize proposal settings
        from .utils.utils_api import update_proposal_settings_from_api
        update_proposal_settings_from_api()    
        
        if "runserver" in sys.argv:
            # if settings.DEBUG:
            # Import and send startup signal here
            from .signals import startup_signal
            startup_signal.send(sender=startup_signal)
