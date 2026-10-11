"""Entry point: parses the map, computes drone routes, and displays
them."""

import sys
from typing import Dict, List, Tuple

from parser import ParseError, Parser
from router import PathStep, SpaceTimeRouter
from visualizer import Visualizer


class Simulation:
    """Orchestrates parsing, routing, and output for one Fly-in run."""

    def __init__(
        self,
        map_path: str,
        use_visualizer: bool,
        show_details: bool = False
    ) -> None:
        """Store the simulation's configuration.

        Args:
            map_path: Path to the map file to simulate.
            use_visualizer: Whether to open the pygame visualizer once
                the routes have been computed and printed.
        """
        self.map_path = map_path
        self.use_visualizer = use_visualizer
        self.show_details = show_details
        self.parser = Parser()
        self.routes: Dict[str, List[PathStep]] = {}

    @classmethod
    def from_argv(cls, argv: List[str]) -> "Simulation":
        """Build a Simulation from command-line arguments.

        Args:
            argv: Arguments following the program name (sys.argv[1:]).

        Returns:
            A configured Simulation, ready to run.
        """
        if not argv:
            print(
                "Usage: ./fly-in <map_path.txt> [--visual]",
                file=sys.stderr,
            )
            sys.exit(1)

        use_visualizer = "--visual" in argv
        map_path = ""
        for arg in argv:
            if not arg.startswith("--"):
                map_path = arg
                break

        if not map_path:
            print(
                "Error: Please provide a map file.",
                file=sys.stderr,
            )
            sys.exit(1)

        return cls(map_path, use_visualizer)

    def run(self) -> None:
        """Parse the map, compute the routes, print the turn-by-turn
        trace, and optionally launch the visualizer."""
        self._parse_map()
        self._compute_routes()
        self._print_trace()
        if self.use_visualizer:
            self._visualize()

    def _parse_map(self) -> None:
        """Parse the map file, exiting the program on any parsing
        error."""
        try:
            self.parser.parse_file(self.map_path)
        except ParseError as e:
            print(f"Parsing error: {e}", file=sys.stderr)
            sys.exit(1)

        if self.parser.start_zone is None or self.parser.end_zone is None:
            print(
                "Error: The start or end zone is not defined "
                "in the map.",
                file=sys.stderr,
            )
            sys.exit(1)

    def _compute_routes(self) -> None:
        """Run the router, exiting the program if no valid schedule
        exists for every drone."""
        assert self.parser.start_zone is not None
        assert self.parser.end_zone is not None

        router = SpaceTimeRouter(self.parser.zones, self.parser.connections)
        try:
            self.routes = router.compute_all_routes(
                self.parser.nb_drones,
                self.parser.start_zone,
                self.parser.end_zone,
            )
        except ValueError as e:
            print(f"Routing error: {e}", file=sys.stderr)
            sys.exit(1)

    def _details_for_turn(self, turn: int) -> str:
        """Describe zone and link occupancy at the end of a turn.

        Args:
            turn: The simulation turn to describe.

        Returns:
            ' | zone:<name> <n>/max:<max> ... | link:<a-b> <n>/cap:<max> ...'
        """
        zones: Dict[str, int] = {}
        links: Dict[Tuple[str, str], int] = {}
        for path in self.routes.values():
            steps = [(lb, t) for lb, t, conn in path if not conn]
            for (a, t_a), (b, t_b) in zip(steps, steps[1:]):
                if t_b == turn:
                    zones[b] = zones.get(b, 0) + 1
                if a != b and t_a < turn <= t_b:
                    key = (min(a, b), max(a, b))
                    links[key] = links.get(key, 0) + 1

        caps = {c.key: c.max_link_capacity for c in self.parser.connections}
        zone_txt = " ".join(
            f"zone:{n} {c}/max:{self.parser.zones[n].max_drones}"
            for n, c in zones.items()
        )
        link_txt = " ".join(
            f"link:{k[0]}-{k[1]} {c}/cap:{caps[k]}" for k, c in links.items()
        )
        return f" | {zone_txt} | {link_txt}"

    def _print_trace(self) -> None:
        """Print the turn-by-turn movement trace, in the format required
        by the subject (VII.5): one line per turn, space-separated
        'D<id>-<label>' actions, drones that did not move omitted."""
        max_turns = max(
            (tour for path in self.routes.values() for _, tour, _ in path),
            default=0,
        )

        for turn in range(1, max_turns + 1):
            actions = self._actions_for_turn(turn)
            if actions:
                line = " ".join(actions)
                print(line)

    def _actions_for_turn(self, turn: int) -> List[str]:
        """Build the list of 'D<id>-<label>' actions for a single turn.

        Args:
            turn: The simulation turn to build actions for.

        Returns:
            One 'D<id>-<label>' string per drone that moved during
            `turn` (a drone that merely waited in place is skipped).
        """
        actions: List[str] = []
        for drone_id, path in self.routes.items():
            prev_label = self._label_at(path, turn - 1)
            for label, tour, is_conn in path:
                if tour != turn:
                    continue
                if not is_conn and label == prev_label:
                    continue
                actions.append(f"D{drone_id[1:]}-{label}")
                break
        return actions

    @staticmethod
    def _label_at(path: List[PathStep], turn: int) -> str:
        """Return the label (zone or connection) a drone is at on a
        given turn.

        Args:
            path: The drone's full path.
            turn: The turn to query.

        Returns:
            The label at that turn, or an empty string if not found.
        """
        result = ""
        for label, tour, _is_conn in path:
            if tour <= turn:
                result = label
            else:
                break
        return result

    def _visualize(self) -> None:
        """Launch the pygame visualizer, exiting the program on any
        unexpected error."""
        try:
            Visualizer(
                self.parser.zones, self.parser.connections, self.routes
            ).run()
        except Exception as e:
            print(f"Visualizer error: {e}", file=sys.stderr)
            sys.exit(1)


def main() -> None:
    """Program entry point."""
    try:
        Simulation.from_argv(sys.argv[1:]).run()
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
