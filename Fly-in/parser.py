import re
from typing import Dict, Iterable, List, Optional, Set, Tuple

from models import Connection, Zone, ZoneType

HUB_METADATA_KEYS = {"zone", "color", "max_drones"}
CONNECTION_METADATA_KEYS = {"max_link_capacity"}
ALL_METADATA_KEYS = HUB_METADATA_KEYS | CONNECTION_METADATA_KEYS

HUB_PREFIXES = ("start_hub", "end_hub", "hub")

_INT_RE = re.compile(r"-?[0-9]+")
_POSITIVE_INT_RE = re.compile(r"[0-9]+")
_ZONE_NAME_RE = re.compile(r"[^\s\-]+")


class ParseError(ValueError):
    """Erreur de syntaxe ou de validation dans un fichier de carte."""


class Parser:
    """Analyse un fichier de carte Fly-in et valide sa cohérence.

    Attributes:
        zones: Zones de la carte, indexées par leur nom.
        connections: Connexions (bidirectionnelles) entre les zones.
        nb_drones: Nombre de drones (0 tant que non défini).
        start_zone: Zone de départ (None tant que non définie).
        end_zone: Zone d'arrivée (None tant que non définie).
    """

    def __init__(self) -> None:
        """Initialise un parseur vide."""
        self.zones: Dict[str, Zone] = {}
        self.connections: List[Connection] = []
        self.nb_drones: int = 0
        self.start_zone: Optional[Zone] = None
        self.end_zone: Optional[Zone] = None
        self._connection_keys: Set[Tuple[str, str]] = set()

    def parse_file(self, file_path: str) -> None:
        """Lit et valide un fichier de carte.

        Args:
            file_path: Chemin du fichier de carte.

        Raises:
            ParseError: Fichier illisible ou carte invalide.
        """
        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                content = f.read()
        except UnicodeDecodeError as e:
            raise ParseError(
                f"Le fichier '{file_path}' n'est pas en UTF-8 valide."
            ) from e
        except OSError as e:
            raise ParseError(
                f"Impossible de lire '{file_path}' : {e.strerror}"
            ) from e
        self.parse_lines(content.split("\n"))

    def parse_lines(self, lines: Iterable[str]) -> None:
        """Analyse les lignes d'une carte puis valide la carte complète.

        Args:
            lines: Lignes du fichier (sans contrainte sur les fins de ligne).

        Raises:
            ParseError: Ligne invalide (avec son numéro) ou carte incohérente.
        """
        for line_num, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                self._parse_line(line)
            except ParseError as e:
                raise ParseError(f"[Ligne {line_num}] {e}") from e
        self._validate_map()

    def _parse_line(self, line: str) -> None:
        """Aiguille une ligne vers le bon traitement selon son mot-clé."""
        keyword, sep, rest = line.partition(":")
        keyword = keyword.strip()
        if not sep:
            raise ParseError(
                f"Format de ligne non reconnu : '{line}' "
                "(attendu 'mot-clé: valeur')"
            )

        if keyword == "nb_drones":
            self._parse_nb_drones(rest)
            return

        if keyword not in HUB_PREFIXES and keyword != "connection":
            raise ParseError(
                f"Mot-clé non reconnu : '{keyword}' (attendu : nb_drones, "
                "start_hub, end_hub, hub ou connection)"
            )
        if self.nb_drones == 0:
            raise ParseError(
                "La première ligne utile doit être "
                "'nb_drones: <entier positif>'."
            )

        if keyword == "connection":
            self._parse_connection(rest)
        else:
            self._parse_hub(keyword, rest)

    def _parse_nb_drones(self, value: str) -> None:
        """Traite 'nb_drones: <entier positif>' (une seule fois)."""
        if self.nb_drones != 0:
            raise ParseError("'nb_drones' est défini plusieurs fois.")
        self.nb_drones = self._parse_positive_int(value.strip(), "nb_drones")

    def _parse_hub(self, prefix: str, rest: str) -> None:
        """Traite une ligne start_hub / end_hub / hub.

        Args:
            prefix: 'start_hub', 'end_hub' ou 'hub'.
            rest: Texte situé après les deux-points.
        """
        is_start = prefix == "start_hub"
        is_end = prefix == "end_hub"

        body, meta_str = self._split_metadata(rest)
        tokens = body.split()
        if len(tokens) != 3:
            raise ParseError(
                f"Format de hub invalide : '{body}' (attendu : "
                "'<nom> <x> <y> [métadonnées]', le nom ne doit contenir "
                "ni espace ni tiret)"
            )
        name, x_str, y_str = tokens

        if "-" in name:
            raise ParseError(f"Le nom '{name}' ne doit pas contenir de tiret.")
        if name in self.zones:
            raise ParseError(f"Zone en doublon : '{name}'.")
        if is_start and self.start_zone is not None:
            raise ParseError("'start_hub' est défini plusieurs fois.")
        if is_end and self.end_zone is not None:
            raise ParseError("'end_hub' est défini plusieurs fois.")

        x = self._parse_coordinate(x_str, "x")
        y = self._parse_coordinate(y_str, "y")

        meta = self.parse_metadata(meta_str, HUB_METADATA_KEYS, "un hub")

        zone_type = self._parse_zone_type(meta.get("zone", "normal"))
        if (is_start or is_end) and zone_type == ZoneType.BLOCKED:
            raise ParseError(
                f"Le hub '{name}' ({prefix}) ne peut pas être 'blocked'."
            )

        if is_start or is_end:
            max_drones = self.nb_drones
        else:
            max_drones = self._parse_positive_int(
                meta.get("max_drones", "1"), "max_drones"
            )

        color = meta.get("color")

        zone = Zone(name, x, y, zone_type, max_drones, color)
        self.zones[name] = zone
        if is_start:
            self.start_zone = zone
        elif is_end:
            self.end_zone = zone

    def _parse_connection(self, rest: str) -> None:
        """Traite 'connection: <zone1>-<zone2> [max_link_capacity=N]'."""
        body, meta_str = self._split_metadata(rest)

        parts = body.split("-")
        if len(parts) > 2:
            raise ParseError(
                f"Connexion invalide : '{body}' (les noms de zones ne "
                "peuvent pas contenir de tiret)"
            )
        if len(parts) != 2 or not all(
            _ZONE_NAME_RE.fullmatch(p) for p in parts
        ):
            raise ParseError(
                f"Format de connexion invalide : '{body}' "
                "(attendu : '<zone1>-<zone2> [métadonnées]', "
                "sans espace autour du tiret)"
            )
        z1_name, z2_name = parts

        for name in (z1_name, z2_name):
            if name not in self.zones:
                raise ParseError(
                    f"Zone inconnue dans la connexion : '{name}' "
                    "(elle doit être définie avant la connexion)."
                )
        if z1_name == z2_name:
            raise ParseError(
                f"Une zone ne peut pas être reliée à elle-même : '{z1_name}'."
            )

        key = (min(z1_name, z2_name), max(z1_name, z2_name))
        if key in self._connection_keys:
            raise ParseError(f"Connexion en doublon : {z1_name}-{z2_name}.")

        meta = self.parse_metadata(
            meta_str, CONNECTION_METADATA_KEYS, "une connexion"
        )
        max_link = self._parse_positive_int(
            meta.get("max_link_capacity", "1"), "max_link_capacity"
        )

        self._connection_keys.add(key)
        self.connections.append(
            Connection(self.zones[z1_name], self.zones[z2_name], max_link)
        )

    @staticmethod
    def _split_metadata(text: str) -> Tuple[str, str]:
        """Sépare le corps d'une ligne de son bloc '[...]' éventuel.

        Args:
            text: Texte situé après les deux-points.

        Returns:
            Tuple (corps, contenu des crochets). Le contenu est une chaîne
            vide s'il n'y a pas de bloc de métadonnées.

        Raises:
            ParseError: Crochets manquants, multiples ou imbriqués, ou texte
                placé après le crochet fermant.
        """
        text = text.strip()
        start = text.find("[")
        if start == -1:
            if "]" in text:
                raise ParseError(f"Crochet fermant ']' sans '[' : '{text}'")
            return text, ""

        body = text[:start].strip()
        block = text[start:]
        if not block.endswith("]"):
            raise ParseError(
                f"Bloc de métadonnées mal formé : '{block}' (crochet "
                "fermant manquant, ou texte après ']')"
            )
        inner = block[1:-1]
        if "[" in inner or "]" in inner:
            raise ParseError(
                f"Un seul bloc '[...]' est autorisé, sans crochets "
                f"imbriqués : '{block}'"
            )
        return body, inner

    def parse_metadata(
        self, meta_str: str, allowed_keys: Set[str], context: str
    ) -> Dict[str, str]:
        """Analyse le contenu d'un bloc de métadonnées 'clé=valeur ...'.

        Args:
            meta_str: Contenu entre crochets (peut être vide).
            allowed_keys: Clés autorisées pour ce type de ligne.
            context: Libellé du type de ligne, pour les messages d'erreur.

        Returns:
            Dictionnaire clé -> valeur (les valeurs restent des chaînes).

        Raises:
            ParseError: Clé inconnue, mal placée, en doublon, ou syntaxe
                invalide.
        """
        meta: Dict[str, str] = {}
        for token in meta_str.split():
            key, sep, value = token.partition("=")
            if not sep or not key or not value or "=" in value:
                raise ParseError(
                    f"Métadonnée invalide : '{token}' "
                    "(format attendu : clé=valeur, sans espace autour de '=')"
                )
            if key not in ALL_METADATA_KEYS:
                raise ParseError(f"Métadonnée non reconnue : '{key}'.")
            if key not in allowed_keys:
                raise ParseError(
                    f"La métadonnée '{key}' n'est pas valide pour {context} "
                    f"(autorisées : {', '.join(sorted(allowed_keys))})."
                )
            if key in meta:
                raise ParseError(f"Métadonnée en doublon : '{key}'.")
            meta[key] = value
        return meta

    @staticmethod
    def _parse_positive_int(value: str, label: str) -> int:
        """Convertit une chaîne en entier strictement positif.

        Args:
            value: Chaîne à convertir.
            label: Nom du champ, pour le message d'erreur.

        Raises:
            ParseError: La valeur n'est pas un entier strictement positif.
        """
        if not _POSITIVE_INT_RE.fullmatch(value) or int(value) <= 0:
            raise ParseError(
                f"{label} invalide : '{value}' "
                "(doit être un entier strictement positif)."
            )
        return int(value)

    @staticmethod
    def _parse_coordinate(value: str, axis: str) -> int:
        """Convertit une coordonnée en entier (négatif autorisé)."""
        if not _INT_RE.fullmatch(value):
            raise ParseError(
                f"Coordonnée {axis} invalide : '{value}' (entier attendu)."
            )
        return int(value)

    @staticmethod
    def _parse_zone_type(value: str) -> ZoneType:
        """Convertit une chaîne en ZoneType.

        Raises:
            ParseError: Le type n'est pas l'un des types du sujet.
        """
        try:
            return ZoneType(value)
        except ValueError:
            valid = ", ".join(t.value for t in ZoneType)
            raise ParseError(
                f"Type de zone invalide : '{value}' (attendu : {valid})."
            ) from None

    def _validate_map(self) -> None:
        """Vérifie la cohérence de la carte une fois toutes les lignes lues.

        Raises:
            ParseError: nb_drones, start_hub ou end_hub manquant, ou aucun
                chemin possible entre le départ et l'arrivée.
        """
        if self.nb_drones == 0:
            raise ParseError(
                "Le fichier doit définir 'nb_drones: <entier positif>' "
                "en première ligne utile."
            )
        if self.start_zone is None:
            raise ParseError("La carte doit définir un 'start_hub:'.")
        if self.end_zone is None:
            raise ParseError("La carte doit définir un 'end_hub:'.")
        if not self._is_reachable(self.start_zone, self.end_zone):
            raise ParseError(
                f"Aucun chemin entre '{self.start_zone.name}' et "
                f"'{self.end_zone.name}' (carte non connectée ou chemin "
                "coupé par des zones 'blocked')."
            )

    def _is_reachable(self, start: Zone, end: Zone) -> bool:
        """Parcours en largeur ignorant les zones 'blocked'.

        Args:
            start: Zone de départ.
            end: Zone d'arrivée.

        Returns:
            True s'il existe au moins un chemin de start à end.
        """
        neighbors: Dict[str, List[str]] = {name: [] for name in self.zones}
        for conn in self.connections:
            neighbors[conn.zone1.name].append(conn.zone2.name)
            neighbors[conn.zone2.name].append(conn.zone1.name)

        seen: Set[str] = {start.name}
        stack: List[str] = [start.name]
        while stack:
            current = stack.pop()
            if current == end.name:
                return True
            for other in neighbors[current]:
                if other in seen:
                    continue
                if self.zones[other].zone_type == ZoneType.BLOCKED:
                    continue
                seen.add(other)
                stack.append(other)
        return False
