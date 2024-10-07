from django.core.management.base import BaseCommand
from prop_api.propsettings_app.factories_from_package import populate_tables


class Command(BaseCommand):
    help = "Populate the database tables from Pydantic classes"

    def handle(self, *args, **kwargs):
        self.stdout.write("Populating the database tables...")
        populate_tables()
        self.stdout.write("Database tables populated successfully.")
