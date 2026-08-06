import sys

from parser import Parser
from router import SpaceTimeRouter
from visualizer import run_visualizer
from typing import List


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: ./fly-in <chemin_de_la_carte.txt> [--visual]",
            file=sys.stderr
        )
        sys.exit(1)

    use_visualizer = "--visual" in sys.argv

    map_path = ""
    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            map_path = arg
            break

    if not map_path:
        print(
            "Erreur : Veuillez spécifier un fichier de carte.",
            file=sys.stderr
        )
        sys.exit(1)

    p = Parser()
    try:
        p.parse_file(map_path)
    except Exception as e:
        print(f"Erreur de parsing : {e}", file=sys.stderr)
        sys.exit(1)

    if p.start_zone is None or p.end_zone is None:
        print(
            "Erreur : La zone de départ ou "
            "d'arrivée n'est pas définie dans la carte.",
            file=sys.stderr,
        )
        sys.exit(1)

    router = SpaceTimeRouter(p.zones, p.connections)
    routes = router.compute_all_routes(p.nb_drones, p.start_zone, p.end_zone)

    max_turns = max(tour for path in routes.values() for _, tour in path)

    for t in range(1, max_turns + 1):
        turn_actions: List[str] = []
        for drone_id, path in routes.items():
            for zone_name, tour in path:
                if tour == t:
                    turn_actions.append(f"D{drone_id[1:]}-{zone_name}")
                    break
        if turn_actions:
            print(" ".join(turn_actions))

    if use_visualizer:
        run_visualizer(p.zones, p.connections, routes)


if __name__ == "__main__":
    main()
