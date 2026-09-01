from enum import Enum
from typing import Dict, List, Optional


class ZoneType(Enum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class Zone:
    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone_type: ZoneType = ZoneType.NORMAL,
        max_drones: int = 1,
        color: Optional[str] = None,
    ) -> None:
        self.name: str = name
        self.x: int = x
        self.y: int = y
        self.zone_type: ZoneType = zone_type
        self.max_drones: int = max_drones
        self.color: Optional[str] = color
        self.current_drones: List[str] = []

    @property
    def cost(self) -> int:
        if self.zone_type == ZoneType.RESTRICTED:
            return 2
        return 1

    @property
    def priority_bonus(self) -> int:
        """Petit bonus négatif pour favoriser les zones priority
        à coût égal dans le tri de la priority queue."""
        return -1 if self.zone_type == ZoneType.PRIORITY else 0

    def is_full(self, count: int) -> bool:
        return count >= self.max_drones


class Connection:
    def __init__(
        self,
        zone1: Zone,
        zone2: Zone,
        max_link_capacity: int = 1,
    ) -> None:
        self.zone1: Zone = zone1
        self.zone2: Zone = zone2
        self.max_link_capacity: int = max_link_capacity
        self.drones_in_transit: Dict[str, int] = {}

    @property
    def key(self) -> tuple[str, str]:
        """Clé canonique (triée) identifiant la connexion,
        indépendamment du sens de parcours."""
        names = sorted([self.zone1.name, self.zone2.name])
        return (names[0], names[1])

    def other(self, zone_name: str) -> Zone:
        """Retourne l'autre extrémité de la connexion."""
        if self.zone1.name == zone_name:
            return self.zone2
        return self.zone1
