import sys
from typing import List, Dict

from parser import ParseError, Parser
from router import PathStep, SpaceTimeRouter
from visualizer import run_visualizer


def main() -> None:
    """Point d'entrée : parse la carte, calcule les routes, affiche."""
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
    except ParseError as e:
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
    try:
        routes = router.compute_all_routes(
            p.nb_drones, p.start_zone, p.end_zone
        )
    except ValueError as e:
        print(f"Erreur de routage : {e}", file=sys.stderr)
        sys.exit(1)

    max_turns = max(
        (tour for path in routes.values() for _, tour, _ in path),
        default=0,
    )

    link_caps = {
        f"{c.key[0]}_{c.key[1]}":
        c.max_link_capacity for c in p.connections
    }

    for t in range(1, max_turns + 1):
        turn_actions: List[str] = []
        zone_counts: Dict[str, int] = {z: 0 for z in p.zones}
        link_counts: Dict[str, int] = {}

        for drone_id, path in routes.items():
            curr_pos = _label_at(path, t)
            if curr_pos in p.zones:
                zone_counts[curr_pos] += 1
            elif curr_pos:
                link_counts[curr_pos] = link_counts.get(curr_pos, 0) + 1

            for label, tour, is_conn in path:
                if tour != t:
                    continue

                prev_label = _label_at(path, t - 1)
                if not is_conn and label == prev_label:
                    continue

                turn_actions.append(f"D{drone_id[1:]}-{label}")
                break
        if turn_actions:
            z_info = " ".join(
                f"{z}={cnt}/{p.zones[z].max_drones}"
                for z, cnt in zone_counts.items() if cnt > 0
            )

            l_info = " ".join(
                f"{lk}={cnt}/{link_caps.get(lk, 1)}"
                for lk, cnt in link_counts.items() if cnt > 0
            )
            details = f" | {z_info}" if z_info else ""
            if l_info:
                details += f" | {l_info}"

            print(" ".join(turn_actions))

    if use_visualizer:
        try:
            run_visualizer(p.zones, p.connections, routes)
        except Exception as e:
            print(f"Erreur du visualiseur : {e}", file=sys.stderr)
            sys.exit(1)


def _label_at(path: List[PathStep], turn: int) -> str:
    """Retourne le label (zone ou connexion) où se trouve le drone
    à un tour donné, ou chaîne vide si non trouvé."""
    result = ""
    for label, tour, _is_conn in path:
        if tour <= turn:
            result = label
        else:
            break
    return result


if __name__ == "__main__":
    main()
