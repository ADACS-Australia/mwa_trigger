import sys

from django.apps import AppConfig
from django.conf import settings
from django.core.checks import Tags, Warning, register


class TriggerAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "trigger_app"

    def ready(self):
        import trigger_app.signals
        from trigger_app.utils.utils_api import initialize_api_session

        # from trigger_app.utils.utils_update import \
        #     update_proposal_settings_from_api
        # Initialize API session
        initialize_api_session()
        # Initialize proposal settings
        # update_proposal_settings_from_api()

        if "runserver" in sys.argv:
            # if settings.DEBUG:
            # Import and send startup signal here
            from .signals import startup_signal

            startup_signal.send(sender=startup_signal)
