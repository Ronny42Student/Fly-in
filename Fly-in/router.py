"""Space-time Dijkstra routing engine for the drone fleet."""

import heapq
import itertools
from typing import Dict, List, Optional, Set, Tuple

from models import Connection, Zone, ZoneType


PathStep = Tuple[str, int, bool]


class SpaceTimeRouter:
    """Computes conflict-free, turn-by-turn paths for a fleet of drones.

    Each drone is routed independently, one after another (a technique
    known as prioritized planning), over a space-time expanded graph:
    every state explored is a pair (zone name, turn number), which lets
    the router know that a zone can be occupied right now but free again
    a few turns later. Once a drone's path is found, it is reserved so
    that every later drone routes around it.
    """

    def __init__(
        self,
        zones: Dict[str, Zone],
        connections: List[Connection],
    ) -> None:
        """Build the router's adjacency list from the map's zones and
        connections.

        Args:
            zones: Map zones, indexed by name.
            connections: Bidirectional connections between zones.
        """
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
        """Compute the optimal route for every drone, one after another.

        Args:
            nb_drones: Number of drones to route.
            start: Starting zone, shared by every drone.
            end: Destination zone.

        Returns:
            Dictionary mapping each drone id ("d1", "d2", ...) to its
            path.

        Raises:
            ValueError: If a drone cannot reach the destination given
                the traffic already reserved by earlier drones.
        """
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
        """Find the fastest conflict-free path for a single drone.

        Runs a Dijkstra search over (zone, turn) states. The priority
        queue is ordered primarily by arrival turn, so the path with the
        fewest turns is always found first — matching the subject's
        scoring rule that turn count is the primary metric — and only
        secondarily by an accumulated "priority score", which breaks
        ties between equally-fast paths in favor of routes that use more
        PRIORITY zones, as required by the subject.

        Args:
            start: Starting zone.
            end: Destination zone.

        Returns:
            The path as a list of (label, turn, is_connection) steps, or
            None if no valid path exists within the turn horizon.
        """
        counter = itertools.count()

        queue: List[Tuple[int, int, int, str, List[PathStep]]] = []
        heapq.heappush(
            queue,
            (0, 0, next(counter), start.name, [(start.name, 0, False)]),
        )

        visited: Set[Tuple[str, int]] = set()

        max_tour = self.max_tour

        while queue:
            tour, priority_score, _, curr_name, path = heapq.heappop(queue)

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
                        next_tour,
                        priority_score,
                        next(counter),
                        curr_name,
                        path + [(curr_name, next_tour, False)],
                    ),
                )

            for neighbor, conn in self.adj[curr_name]:
                if neighbor.zone_type == ZoneType.BLOCKED:
                    continue

                is_restricted = neighbor.zone_type == ZoneType.RESTRICTED
                travel_cost = 2 if is_restricted else 1
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
                            arrival_tour,
                            priority_score + neighbor.priority_bonus,
                            next(counter),
                            neighbor.name,
                            new_path,
                        ),
                    )
        return None

    def _reserve_path(self, path: List[PathStep]) -> None:
        """Record a found path's zone and connection usage so that every
        later drone plans around it.

        Args:
            path: The path to reserve, as returned by
                `_find_path_for_drone`.
        """
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
