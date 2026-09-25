"""Data model for the Fly-in simulation: zones, connections and zone
types."""

from enum import Enum
from typing import Dict, List, Optional, Tuple


class ZoneType(Enum):
    """The four zone types defined by the subject.

    NORMAL zones cost 1 turn to enter, BLOCKED zones can never be
    entered, RESTRICTED zones cost 2 turns to enter, and PRIORITY zones
    cost 1 turn but should be favored by the router when several paths
    tie on total turn count.
    """

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class Zone:
    """A single zone (node) of the map graph.

    Attributes:
        name: Unique name of the zone.
        x: X coordinate on the map.
        y: Y coordinate on the map.
        zone_type: The zone's ZoneType.
        max_drones: Maximum number of drones allowed simultaneously.
        color: Optional color name used for visual representation.
        current_drones: List of drone identifiers currently in the zone.
    """

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone_type: ZoneType = ZoneType.NORMAL,
        max_drones: int = 1,
        color: Optional[str] = None,
    ) -> None:
        """Initialize a zone.

        Args:
            name: Unique name of the zone.
            x: X coordinate on the map.
            y: Y coordinate on the map.
            zone_type: The zone's type (defaults to NORMAL).
            max_drones: Maximum simultaneous drone capacity.
            color: Optional color name for visual representation.
        """
        self.name: str = name
        self.x: int = x
        self.y: int = y
        self.zone_type: ZoneType = zone_type
        self.max_drones: int = max_drones
        self.color: Optional[str] = color
        self.current_drones: List[str] = []

    @property
    def cost(self) -> int:
        """Movement cost, in turns, required to enter this zone."""
        if self.zone_type == ZoneType.RESTRICTED:
            return 2
        return 1

    @property
    def priority_bonus(self) -> int:
        """Small negative bonus used by the router to favor PRIORITY
        zones when several paths tie on total turn count."""
        return -1 if self.zone_type == ZoneType.PRIORITY else 0

    def is_full(self, count: int) -> bool:
        """Return True if `count` drones already fill this zone's
        capacity.

        Args:
            count: Number of drones currently considered to be in the
                zone.

        Returns:
            True if the zone cannot accept another drone.
        """
        return count >= self.max_drones


class Connection:
    """A bidirectional connection (edge) between two zones."""

    def __init__(
        self,
        zone1: Zone,
        zone2: Zone,
        max_link_capacity: int = 1,
    ) -> None:
        """Initialize a connection between two zones.

        Args:
            zone1: One endpoint of the connection.
            zone2: The other endpoint of the connection.
            max_link_capacity: Maximum number of drones allowed to
                traverse the connection simultaneously.
        """
        self.zone1: Zone = zone1
        self.zone2: Zone = zone2
        self.max_link_capacity: int = max_link_capacity
        self.drones_in_transit: Dict[str, int] = {}

    @property
    def key(self) -> Tuple[str, str]:
        """Canonical (sorted) key identifying the connection,
        independent of the direction it is traversed in."""
        names = sorted([self.zone1.name, self.zone2.name])
        return (names[0], names[1])

    def other(self, zone_name: str) -> Zone:
        """Return the endpoint of the connection other than `zone_name`.

        Args:
            zone_name: Name of the endpoint already known.

        Returns:
            The zone at the other end of the connection.
        """
        if self.zone1.name == zone_name:
            return self.zone2
        return self.zone1
