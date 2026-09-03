import re
import pygame
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

        meta_str = meta_str.strip()
        if meta_str.startswith("[") and meta_str.endswith("]"):
            meta_str = meta_str[1:-1].strip()

        if not meta_str:
            return meta_data

        tokens = meta_str.split()
        i = 0
        while i < len(tokens):
            token = tokens[i]

            if "=" in token:
                key, _, value = token.partition("=")
                if not key or not value:
                    raise ValueError(f"Métadonnée invalide : '{token}'")
                if key in meta_data:
                    raise ValueError(
                        f"Métadonnée en doublon : '{key}'"
                    )

                meta_data[key.strip()] = value.strip()
                i += 1

            elif token.lower() in ("zone", "color"):
                key = token.lower()

                if i + 1 >= len(tokens):
                    raise ValueError(
                        f"Valeur manquante pour la métadonnée '{token}'"
                    )

                if key in meta_data:
                    raise ValueError(
                        f"Métadonnée en doublon : '{key}'"
                    )

                meta_data[token.lower()] = tokens[i + 1]
                i += 2
            else:
                raise ValueError(f"Métadonnée non reconnue : '{token}'")

        return meta_data

    def parse_file(self, file_path: str) -> None:
        with open(file_path, "r") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                try:
                    if (
                        line.startswith("nb_drones:")
                    ):
                        self.nb_drones = int(line.split(":")[1].strip())
                        if self.nb_drones <= 0:
                            raise ValueError(
                                "Le nombre de drones doit être positif."
                            )
                        continue

                    hub_match = re.match(
                        r"^(start_hub|end_hub|hub):"
                        r"\s*([^\s\[\-]+)\s+(-?\d+)\s"
                        r"+(-?\d+)(?:\s+\[([a-zA-Z0-9_=\s]+)\])?$",
                        line,
                    )
                    if hub_match:
                        (
                            prefix,
                            name,
                            x_str,
                            y_str,
                            meta_str
                        ) = hub_match.groups()

                        if "-" in name:
                            raise ValueError(
                                f"Le nom '{name}' ne doit"
                                " pas contenir de tiret."
                            )
                        if name in self.zones:
                            raise ValueError(f"Zone en doublon : '{name}'.")

                        meta = self.parse_metadata(
                            meta_str if meta_str
                            else ""
                        )
                        z_type_str = meta.get("zone", "normal")
                        try:
                            z_type = ZoneType(z_type_str)
                        except ValueError:
                            raise ValueError("Type de zone invalide"
                                             f" : '{z_type_str}'.")

                        max_drones_str = meta.get("max_drones", "1")
                        if (
                            not max_drones_str.isdigit() or
                            int(max_drones_str) <= 0
                        ):
                            raise ValueError(
                                f"max_drones invalide : '{max_drones_str}' "
                                "(doit être un entier positif)"
                            )

                        max_drones = int(max_drones_str)

                        KNOW_SPECIAL_COLORS = {"rainbow"}

                        color = meta.get("color", None)
                        if (
                            color is not None and
                            color not in KNOW_SPECIAL_COLORS
                        ):
                            try:
                                pygame.Color(color)
                            except ValueError:
                                raise ValueError(
                                    f"Couleur invalide : '{color}'"
                                )

                        zone = Zone(
                            name,
                            int(x_str),
                            int(y_str),
                            z_type,
                            max_drones,
                            color
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
                            rest_part = (
                                re.sub(r"\[.*\]", "", rest_part).strip()
                            )

                        if "-" not in rest_part:
                            raise ValueError("Format de connexion"
                                             f" invalide : '{line}'")

                        z1_name, z2_name = rest_part.split("-", 1)
                        z1_name = z1_name.strip()
                        z2_name = z2_name.strip()

                        if (
                            z1_name not in self.zones or
                            z2_name not in self.zones
                        ):
                            raise ValueError("Zone manquante "
                                             f": {z1_name} ou {z2_name}")

                        for existing_conn in self.connections:
                            if {
                                existing_conn.zone1.name,
                                existing_conn.zone2.name
                            } == {
                                z1_name,
                                z2_name,
                            }:
                                raise ValueError(
                                    "Connexion en doublon :"
                                    f" {z1_name}-{z2_name}"
                                )

                        meta = self.parse_metadata(meta_str)
                        max_link_str = meta.get("max_link_capacity", "1")
                        if (
                            not max_link_str.isdigit() or
                            int(max_link_str) <= 0
                        ):
                            raise ValueError(
                                "max_link_capacity invalide :"
                                f" '{max_link_str}' "
                                "(doit être un entier positif)"
                            )
                        max_link = int(max_link_str)
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
                "La carte doit spécifier un "
                "'start_hub:' et un 'end_hub:' valide."
            )
