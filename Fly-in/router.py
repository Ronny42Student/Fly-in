import heapq
from typing import Dict, List, Optional, Set, Tuple

from models import Connection, Zone, ZoneType


class SpaceTimeRouter:
    def __init__(self, zones: Dict[str, Zone], connections: List[Connection]) -> None:
        self.zones = zones
        self.connections = connections

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
    ) -> Dict[str, List[Tuple[str, int]]]:
        """Calcule l'itinéraire optimal pour chaque drone l'un après l'autre"""
        all_paths: Dict[str, List[Tuple[str, int]]] = {}

        for i in range(1, nb_drones + 1):
            drone_id = f"d{i}"
            path = self._find_path_for_drone(start, end)

            if not path:
                raise ValueError(
                    f"Impossible de trouver un itinéraire pour le drone {drone_id}. Bloqué par les contraintes de trafic."
                )

            all_paths[drone_id] = path
            self._reserve_path(path)

        return all_paths

    def _find_path_for_drone(
        self, start: Zone, end: Zone
    ) -> Optional[List[Tuple[str, int]]]:
        queue: List[Tuple[int, int, str, List[Tuple[str, int]]]] = []
        heapq.heappush(queue, (0, 0, start.name, [(start.name, 0)]))

        visited: Set[Tuple[str, int]] = set()

        while queue:
            cost, tour, curr_name, path = heapq.heappop(queue)

            if curr_name == end.name:
                return path

            if (curr_name, tour) in visited:
                continue
            visited.add((curr_name, tour))

            next_tour = tour + 1
            curr_zone = self.zones[curr_name]

            if curr_name in (start.name, end.name) or (
                self.occupied_zones.get((curr_name, next_tour), 0)
                < curr_zone.max_drones
            ):
                heapq.heappush(
                    queue,
                    (
                        cost + 1,
                        next_tour,
                        curr_name,
                        path + [(curr_name, next_tour)],
                    ),
                )

            for neighbor, conn in self.adj[curr_name]:
                if neighbor.zone_type == ZoneType.BLOCKED:
                    continue

                travel_cost = 2 if neighbor.zone_type == ZoneType.RESTRICTED else 1
                arrival_tour = tour + travel_cost

                is_zone_free = (neighbor.name == end.name) or (
                    self.occupied_zones.get((neighbor.name, arrival_tour), 0)
                    < neighbor.max_drones
                )

                sorted_nodes = sorted([curr_name, neighbor.name])
                link_key: Tuple[str, str] = (sorted_nodes[0], sorted_nodes[1])

                is_link_free = (
                    self.occupied_links.get((link_key, tour), 0)
                    < conn.max_link_capacity
                )

                if is_zone_free and is_link_free:
                    heapq.heappush(
                        queue,
                        (
                            cost + travel_cost,
                            arrival_tour,
                            neighbor.name,
                            path + [(neighbor.name, arrival_tour)],
                        ),
                    )
        return None

    def _reserve_path(self, path: List[Tuple[str, int]]) -> None:
        """Enregistre le chemin pour que les drones suivants adaptent leur trajectoire"""
        for i, (zone_name, tour) in enumerate(path):
            if (zone_name, tour) not in self.occupied_zones:
                self.occupied_zones[(zone_name, tour)] = 0
            self.occupied_zones[(zone_name, tour)] += 1

            if i < len(path) - 1:
                next_zone_name, _ = path[i + 1]
                if zone_name != next_zone_name:
                    sorted_nodes = sorted([zone_name, next_zone_name])
                    link_key: Tuple[str, str] = (sorted_nodes[0], sorted_nodes[1])

                    if (link_key, tour) not in self.occupied_links:
                        self.occupied_links[(link_key, tour)] = 0
                    self.occupied_links[(link_key, tour)] += 1
