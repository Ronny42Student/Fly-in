import heapq
from typing import Dict, List, Optional, Set, Tuple

from models import Connection, Zone, ZoneType


PathStep = Tuple[str, int, bool]


class SpaceTimeRouter:
    def __init__(
        self,
        zones: Dict[str, Zone],
        connections: List[Connection]
    ) -> None:
        self.zones = zones
        self.connections = connections

        self.max_tour: int = len(zones) * 10 + 50
        self.occupied_zones: Dict[Tuple[str, int], int] = {}
        self.occupied_links: Dict[Tuple[Tuple[str, str], int], int] = {}

        self.adj: Dict[str, List[Tuple[Zone, Connection]]] = {
            name: [] for name in zones
        }
        for conn in connections:
            self.adj[conn.zone1.name].append((conn.zone2, conn))
            self.adj[conn.zone2.name].append((conn.zone1, conn))

    def compute_all_routes(
        self, nb_drones: int, start: Zone, end: Zone
    ) -> Dict[str, List[PathStep]]:
        """Calcule l'itinéraire optimal
        pour chaque drone l'un après l'autre."""
        all_paths: Dict[str, List[PathStep]] = {}
        self.max_tour = len(self.zones) * 10 + 50 + 2 * nb_drones

        for i in range(1, nb_drones + 1):
            drone_id = f"d{i}"
            path = self._find_path_for_drone(start, end)

            if not path:
                raise ValueError(
                    "Impossible de trouver un itinéraire pour le "
                    f"drone {drone_id}. Bloqué par les contraintes de trafic."
                )

            all_paths[drone_id] = path
            self._reserve_path(path)

        return all_paths

    def _find_path_for_drone(
        self, start: Zone, end: Zone
    ) -> Optional[List[PathStep]]:
        queue: List[Tuple[int, int, str, List[PathStep]]] = []
        heapq.heappush(queue, (0, 0, start.name, [(start.name, 0, False)]))

        visited: Set[Tuple[str, int]] = set()

        max_tour = self.max_tour

        while queue:
            cost, tour, curr_name, path = heapq.heappop(queue)

            if curr_name == end.name:
                return path

            if tour > max_tour:
                continue

            if (curr_name, tour) in visited:
                continue
            visited.add((curr_name, tour))

            next_tour = tour + 1
            curr_zone = self.zones[curr_name]

            if next_tour <= max_tour and (
                curr_name in (start.name, end.name) or
                (
                    self.occupied_zones.get((curr_name, next_tour), 0)
                    < curr_zone.max_drones
                )
            ):
                heapq.heappush(
                    queue,
                    (
                        cost + 1,
                        next_tour,
                        curr_name,
                        path + [(curr_name, next_tour, False)],
                    ),
                )

            for neighbor, conn in self.adj[curr_name]:
                if neighbor.zone_type == ZoneType.BLOCKED:
                    continue

                is_restricted = neighbor.zone_type == ZoneType.RESTRICTED
                travel_cost = 2 if is_restricted else 1
                priority_bonus = neighbor.priority_bonus
                arrival_tour = tour + travel_cost

                if arrival_tour > max_tour:
                    continue

                is_zone_free = (neighbor.name == end.name) or (
                    self.occupied_zones.get((neighbor.name, arrival_tour), 0)
                    < neighbor.max_drones
                )

                link_key = conn.key

                if is_restricted:
                    link_free_depart = (
                        self.occupied_links.get((link_key, tour), 0)
                        < conn.max_link_capacity
                    )
                    link_free_transit = (
                        self.occupied_links.get((link_key, tour + 1), 0)
                        < conn.max_link_capacity
                    )
                    is_link_free = link_free_depart and link_free_transit
                else:
                    is_link_free = (
                        self.occupied_links.get((link_key, tour), 0)
                        < conn.max_link_capacity
                    )

                if is_zone_free and is_link_free:
                    new_path = list(path)
                    if is_restricted:
                        conn_label = f"{link_key[0]}_{link_key[1]}"
                        new_path.append((conn_label, tour + 1, True))
                    new_path.append((neighbor.name, arrival_tour, False))

                    heapq.heappush(
                        queue,
                        (
                            cost + travel_cost + priority_bonus,
                            arrival_tour,
                            neighbor.name,
                            new_path,
                        ),
                    )
        return None

    def _reserve_path(self, path: List[PathStep]) -> None:
        """Enregistre le chemin (zones et connexions en transit) pour
        que les drones suivants adaptent leur trajectoire."""
        zone_steps = [
            (label, tour)
            for label, tour, is_conn in path
            if not is_conn
        ]

        for zone_name, tour in zone_steps:
            key = (zone_name, tour)
            self.occupied_zones[key] = self.occupied_zones.get(key, 0) + 1

        for i, (zone_name, tour) in enumerate(zone_steps[:-1]):
            next_zone_name, next_tour = zone_steps[i + 1]
            if zone_name == next_zone_name:
                continue

            sorted_nodes = sorted([zone_name, next_zone_name])
            link_key: Tuple[str, str] = (sorted_nodes[0], sorted_nodes[1])

            if next_tour - tour == 2:
                for t in (tour, tour + 1):
                    lk = (link_key, t)
                    self.occupied_links[lk] = (
                        self.occupied_links.get(lk, 0) + 1
                    )
            else:
                lk = (link_key, tour)
                self.occupied_links[lk] = self.occupied_links.get(lk, 0) + 1
