from typing import List, Optional

from .models.telescope import EventTelescope


class EventTelescopeFactory:
    """
    A factory class for creating and managing EventTelescope objects.
    """

    @property
    def event_telescope_swift(self):
        return EventTelescope(name="SWIFT")

    @property
    def event_telescope_fermi(self):
        return EventTelescope(name="Fermi")

    @property
    def event_telescope_hess(self):
        return EventTelescope(name="HESS")

    @property
    def event_telescope_antares(self):
        return EventTelescope(name="Antares")

    @property
    def event_telescope_amon(self):
        return EventTelescope(name="AMON")

    @property
    def event_telescope_maxi(self):
        return EventTelescope(name="MAXI")

    @property
    def event_telescope_lvc(self):
        return EventTelescope(name="LVC")

    @property
    def eventtelescopes(self) -> List[EventTelescope]:
        """
        Returns a list of all EventTelescope objects.

        Returns:
            List[EventTelescope]: A list containing all EventTelescope objects.
        """
        # Combine these objects into a list
        return [
            getattr(self, attr)
            for attr in dir(self)
            if attr.startswith("event_telescope_")
            and isinstance(getattr(self, attr), EventTelescope)
        ]

    def get_event_telescope_by_name(self, name: str) -> Optional[EventTelescope]:
        """
        Searches for an EventTelescope object by name.

        Args:
            name (str): The name of the telescope to search for.

        Returns:
            Optional[EventTelescope]: The EventTelescope object if found, None otherwise.
        """
        # Search for the EventTelescope by name
        for telescope in self.eventtelescopes:
            if telescope.name.lower() == name.lower():
                return telescope
        return None
