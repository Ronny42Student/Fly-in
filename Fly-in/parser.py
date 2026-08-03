import re
from typing import Dict, List, Optional

from models import Connection, Zone, ZoneType


class Parser:
    def __init__(self) -> None:
        self.zones: Dict[str, Zone] = {}
        self.connections: List[Connection] = []
        self.nb_drones: int = 0
        self.start_zone: Optional[Zone] = None
        self.end_zone: Optional[Zone] = None

    def parse_metadata(self, meta_str: str) -> Dict[str, str]:
        meta_data: Dict[str, str] = {}
        if not meta_str:
            return meta_data

        meta_str = meta_str.strip("[]")
        items = re.findall(r"(\w+=\w+|\bzone\s+\w+|\bcolor\s+\w+)", meta_str)
        for item in items:
            if "=" in item:
                key, value = item.split("=")
                meta_data[key.strip()] = value.strip()
            elif item.lower().startswith("zone"):
                meta_data["zone"] = item.split()[1]
            elif item.lower().startswith("color"):
                meta_data["color"] = item.split()[1]
        return meta_data

    def parse_file(self, file_path: str) -> None:
        with open(file_path, "r") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                try:
                    if line.startswith("nb drones:") or line.startswith("nb_drones:"):
                        self.nb_drones = int(line.split(":")[1].strip())
                        if self.nb_drones <= 0:
                            raise ValueError("Le nombre de drones doit être positif.")
                        continue

                    hub_match = re.match(
                        r"^(start_hub|end_hub|hub):\s*([^\s\[\-]+)\s+(-?\d+)\s+(-?\d+)(?:\s+\[(.*)\])?$",
                        line,
                    )
                    if hub_match:
                        prefix, name, x_str, y_str, meta_str = hub_match.groups()

                        if "-" in name:
                            raise ValueError(
                                f"Le nom '{name}' ne doit pas contenir de tiret."
                            )
                        if name in self.zones:
                            raise ValueError(f"Zone en doublon : '{name}'.")

                        meta = self.parse_metadata(meta_str if meta_str else "")
                        z_type_str = meta.get("zone", "normal")
                        try:
                            z_type = ZoneType(z_type_str)
                        except ValueError:
                            raise ValueError(f"Type de zone invalide : '{z_type_str}'.")

                        max_drones = int(meta.get("max_drones", 1))
                        color = meta.get("color", None)

                        zone = Zone(
                            name, int(x_str), int(y_str), z_type, max_drones, color
                        )
                        self.zones[name] = zone

                        if prefix == "start_hub":
                            self.start_zone = zone
                        elif prefix == "end_hub":
                            self.end_zone = zone
                        continue

                    if line.startswith("connection:"):
                        rest_part = line.split(":", 1)[1].strip()
                        meta_str = ""
                        meta_match = re.search(r"\[(.*)\]", rest_part)
                        if meta_match:
                            meta_str = meta_match.group(1)
                            rest_part = re.sub(r"\[.*\]", "", rest_part).strip()

                        if "-" not in rest_part:
                            raise ValueError(f"Format de connexion invalide : '{line}'")

                        z1_name, z2_name = rest_part.split("-", 1)
                        z1_name = z1_name.strip()
                        z2_name = z2_name.strip()

                        if z1_name not in self.zones or z2_name not in self.zones:
                            raise ValueError(f"Zone manquante : {z1_name} ou {z2_name}")

                        for existing_conn in self.connections:
                            if {existing_conn.zone1.name, existing_conn.zone2.name} == {
                                z1_name,
                                z2_name,
                            }:
                                raise ValueError(
                                    f"Connexion en doublon : {z1_name}-{z2_name}"
                                )

                        meta = self.parse_metadata(meta_str)
                        max_link = int(meta.get("max_link_capacity", 1))

                        conn = Connection(
                            self.zones[z1_name], self.zones[z2_name], max_link
                        )
                        self.connections.append(conn)
                        continue

                    raise ValueError(f"Format de ligne non reconnu : {line}")

                except Exception as e:
                    raise ValueError(f"[Ligne {line_num}] {e}") from e

        if not self.start_zone or not self.end_zone:
            raise ValueError(
                "La carte doit spécifier un 'start_hub:' et un 'end_hub:' valide."
            )
