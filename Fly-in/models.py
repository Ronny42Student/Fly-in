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
