"""Line-based parser and validator for the Fly-in map file format."""

import re
from typing import Dict, Iterable, List, Optional, Set, Tuple

from design.design_pattern import DesignPattern
from models import Connection, Zone, ZoneType

HUB_METADATA_KEYS = {"zone", "color", "max_drones"}
CONNECTION_METADATA_KEYS = {"max_link_capacity"}
ALL_METADATA_KEYS = HUB_METADATA_KEYS | CONNECTION_METADATA_KEYS

HUB_PREFIXES = ("start_hub", "end_hub", "hub")

_INT_RE = re.compile(r"-?[0-9]+")
_POSITIVE_INT_RE = re.compile(r"[0-9]+")
_ZONE_NAME_RE = re.compile(r"[^\s\-]+")


class ParseError(ValueError):
    """Syntax or validation error found in a map file."""


class Parser:
    """Parses a Fly-in map file and validates its overall consistency.

    Attributes:
        zones: Map zones, indexed by name.
        connections: Bidirectional connections between zones.
        nb_drones: Number of drones (0 until defined).
        start_zone: Starting zone (None until defined).
        end_zone: Destination zone (None until defined).
    """

    def __init__(self) -> None:
        """Initialize an empty parser."""
        self.zones: Dict[str, Zone] = {}
        self.connections: List[Connection] = []
        self.nb_drones: int = 0
        self.start_zone: Optional[Zone] = None
        self.end_zone: Optional[Zone] = None
        self._connection_keys: Set[Tuple[str, str]] = set()

    def parse_file(self, file_path: str) -> None:
        """Read and validate a map file.

        Args:
            file_path: Path to the map file.

        Raises:
            ParseError: If the file cannot be read, or the map is
                invalid.
        """
        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                content = f.read()
        except UnicodeDecodeError as e:
            raise ParseError(
                f"File '{file_path}' is not valid UTF-8."
            ) from e
        except OSError as e:
            raise ParseError(
                f"Unable to read '{file_path}': {e.strerror}"
            ) from e
        self.parse_lines(content.split("\n"))

    def parse_lines(self, lines: Iterable[str]) -> None:
        """Parse a map's lines, then validate the map as a whole.

        Args:
            lines: The file's lines (no constraint on line endings).

        Raises:
            ParseError: If a line is invalid (with its line number), or
                the map is inconsistent once fully parsed.
        """
        for line_num, raw_line in enumerate(lines, start=1):
            line = raw_line.rstrip("\r")
            if not line.strip() or line.startswith("#"):
                continue
            try:
                self._parse_line(line)
            except ParseError as e:
                raise ParseError(f"[Line {line_num}] {e}") from e
        self._validate_map()

    def _parse_line(self, line: str) -> None:
        """Route a single line to the right handler based on its
        keyword.

        Args:
            line: The non-empty, non-comment line to parse, exactly
                as written in the file (spacing is checked here).
        """
        if line != line.strip():
            raise ParseError("Leading or trailing whitespace is not allowed.")
        if "\t" in line:
            raise ParseError("Tabs are not allowed (use single spaces).")

        keyword, sep, rest = line.partition(":")
        if not sep:
            raise ParseError(
                f"Unrecognized line format: '{line}' "
                "(expected 'keyword: value')"
            )
        if keyword != keyword.strip():
            raise ParseError(f"No space is allowed before ':' in '{line}'.")
        if keyword != "nb_drones" and keyword not in HUB_PREFIXES \
                and keyword != "connection":
            raise ParseError(
                f"Unrecognized keyword: '{keyword}' (expected: nb_drones, "
                "start_hub, end_hub, hub or connection)"
            )
        if len(rest) < 2 or rest[0] != " " or rest[1].isspace():
            raise ParseError(
                f"Exactly one space is required after '{keyword}:'."
            )
        value = rest[1:]

        if keyword == "nb_drones":
            self._parse_nb_drones(value)
            return
        if self.nb_drones == 0:
            raise ParseError(
                "The first meaningful line must be "
                "'nb_drones: <positive integer>'."
            )

        if keyword == "connection":
            self._parse_connection(value)
        else:
            self._parse_hub(keyword, value)

    def _parse_nb_drones(self, value: str) -> None:
        """Handle 'nb_drones: <positive integer>' (allowed only once).

        Args:
            value: Text found after the ':' on the nb_drones line.
        """
        if self.nb_drones != 0:
            raise ParseError("'nb_drones' is defined more than once.")
        self.nb_drones = self._parse_positive_int(value, "nb_drones")

    def _parse_hub(self, prefix: str, rest: str) -> None:
        """Handle a start_hub / end_hub / hub line.

        Args:
            prefix: 'start_hub', 'end_hub' or 'hub'.
            rest: Text found after the ':'.
        """
        is_start = prefix == "start_hub"
        is_end = prefix == "end_hub"

        body, meta_str = self._split_metadata(rest)
        tokens = body.split(" ")
        if len(tokens) != 3 or "" in tokens:
            raise ParseError(
                f"Invalid hub format: '{body}' (expected: "
                "'<name> <x> <y> [metadata]' with single spaces; the "
                "name must contain neither spaces nor dashes)"
            )
        name, x_str, y_str = tokens

        if "-" in name:
            raise ParseError(f"Name '{name}' must not contain a dash.")
        if name in self.zones:
            raise ParseError(f"Duplicate zone: '{name}'.")
        if is_start and self.start_zone is not None:
            raise ParseError("'start_hub' is defined more than once.")
        if is_end and self.end_zone is not None:
            raise ParseError("'end_hub' is defined more than once.")

        x = self._parse_coordinate(x_str, "x")
        y = self._parse_coordinate(y_str, "y")

        meta = self.parse_metadata(meta_str, HUB_METADATA_KEYS, "a hub")

        zone_type = self._parse_zone_type(meta.get("zone", "normal"))
        if (is_start or is_end) and zone_type == ZoneType.BLOCKED:
            raise ParseError(
                f"Hub '{name}' ({prefix}) cannot be 'blocked'."
            )

        if is_start or is_end:
            max_drones = self.nb_drones
        else:
            max_drones = self._parse_positive_int(
                meta.get("max_drones", "1"), "max_drones"
            )

        color = meta.get("color")
        if color is not None and color != DesignPattern.RAINBOW_KEYWORD:
            try:
                DesignPattern.color_to_rgb(color)
            except ValueError as e:
                raise ParseError(str(e)) from e

        zone = Zone(name, x, y, zone_type, max_drones, color)
        self.zones[name] = zone
        if is_start:
            self.start_zone = zone
        elif is_end:
            self.end_zone = zone

    def _parse_connection(self, rest: str) -> None:
        """Handle 'connection: <zone1>-<zone2> [max_link_capacity=N]'.

        Args:
            rest: Text found after the ':'.
        """
        body, meta_str = self._split_metadata(rest)

        parts = body.split("-")
        if len(parts) > 2:
            raise ParseError(
                f"Invalid connection: '{body}' (zone names cannot "
                "contain dashes)"
            )
        if len(parts) != 2 or not all(
            _ZONE_NAME_RE.fullmatch(p) for p in parts
        ):
            raise ParseError(
                f"Invalid connection format: '{body}' "
                "(expected: '<zone1>-<zone2> [metadata]', "
                "with no space around the dash)"
            )
        z1_name, z2_name = parts

        for name in (z1_name, z2_name):
            if name not in self.zones:
                raise ParseError(
                    f"Unknown zone in connection: '{name}' "
                    "(it must be defined before the connection)."
                )
        if z1_name == z2_name:
            raise ParseError(
                f"A zone cannot be connected to itself: '{z1_name}'."
            )

        key = (min(z1_name, z2_name), max(z1_name, z2_name))
        if key in self._connection_keys:
            raise ParseError(f"Duplicate connection: {z1_name}-{z2_name}.")

        meta = self.parse_metadata(
            meta_str, CONNECTION_METADATA_KEYS, "a connection"
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
        """Split a line's body from its optional '[...]' metadata block.

        Args:
            text: Text found after the ':'.

        Returns:
            Tuple (body, bracket contents). The contents are an empty
            string when there is no metadata block.

        Raises:
            ParseError: If brackets are missing, duplicated, nested,
                empty, if the spacing before '[' is not a single space,
                or if text follows the closing bracket.
        """
        start = text.find("[")
        if start == -1:
            if "]" in text:
                raise ParseError(
                    f"Closing bracket ']' without '[': '{text}'"
                )
            return text, ""

        body = text[:start]
        if body:
            if not body.endswith(" ") or body.endswith("  "):
                raise ParseError(
                    "Exactly one space is required before '['."
                )
            body = body[:-1]
        block = text[start:]
        if not block.endswith("]"):
            raise ParseError(
                f"Malformed metadata block: '{block}' (missing closing "
                "bracket, or text after ']')"
            )
        inner = block[1:-1]
        if not inner:
            raise ParseError("Empty metadata block '[]'.")
        if "[" in inner or "]" in inner:
            raise ParseError(
                f"Only one '[...]' block is allowed, with no nested "
                f"brackets: '{block}'"
            )
        return body, inner

    def parse_metadata(
        self, meta_str: str, allowed_keys: Set[str], context: str
    ) -> Dict[str, str]:
        """Parse the contents of a 'key=value ...' metadata block.

        Args:
            meta_str: Contents between brackets (may be empty).
            allowed_keys: Keys allowed for this kind of line.
            context: Label for the kind of line, used in error messages.

        Returns:
            Dictionary key -> value (values stay as strings).

        Raises:
            ParseError: If a key is unknown, misplaced, duplicated, or
                the syntax is otherwise invalid.
        """
        meta: Dict[str, str] = {}
        tokens = meta_str.split(" ") if meta_str else []
        for token in tokens:
            if not token:
                raise ParseError(
                    "Metadata entries must be separated by exactly one "
                    "space (no space after '[' or before ']')."
                )
            key, sep, value = token.partition("=")
            if not sep or not key or not value or "=" in value:
                raise ParseError(
                    f"Invalid metadata: '{token}' "
                    "(expected format: key=value, with no space "
                    "around '=')"
                )
            if key not in ALL_METADATA_KEYS:
                raise ParseError(f"Unrecognized metadata: '{key}'.")
            if key not in allowed_keys:
                raise ParseError(
                    f"Metadata '{key}' is not valid for {context} "
                    f"(allowed: {', '.join(sorted(allowed_keys))})."
                )
            if key in meta:
                raise ParseError(f"Duplicate metadata: '{key}'.")
            meta[key] = value
        return meta

    @staticmethod
    def _parse_positive_int(value: str, label: str) -> int:
        """Convert a string into a strictly positive integer.

        Args:
            value: String to convert.
            label: Field name, used in the error message.

        Returns:
            The parsed integer.

        Raises:
            ParseError: If the value is not a strictly positive integer.
        """
        if not _POSITIVE_INT_RE.fullmatch(value) or int(value) <= 0:
            raise ParseError(
                f"Invalid {label}: '{value}' "
                "(must be a strictly positive integer)."
            )
        return int(value)

    @staticmethod
    def _parse_coordinate(value: str, axis: str) -> int:
        """Convert a coordinate into an integer (negative values
        allowed).

        Args:
            value: String to convert.
            axis: Axis name ('x' or 'y'), used in the error message.

        Returns:
            The parsed integer.

        Raises:
            ParseError: If the value is not a valid integer.
        """
        if not _INT_RE.fullmatch(value):
            raise ParseError(
                f"Invalid {axis} coordinate: '{value}' (integer expected)."
            )
        return int(value)

    @staticmethod
    def _parse_zone_type(value: str) -> ZoneType:
        """Convert a string into a ZoneType.

        Args:
            value: String to convert.

        Returns:
            The matching ZoneType.

        Raises:
            ParseError: If the value is not one of the subject's zone
                types.
        """
        try:
            return ZoneType(value)
        except ValueError:
            valid = ", ".join(t.value for t in ZoneType)
            raise ParseError(
                f"Invalid zone type: '{value}' (expected: {valid})."
            ) from None

    def _validate_map(self) -> None:
        """Check the map's overall consistency once every line has been
        read.

        Raises:
            ParseError: If nb_drones, start_hub or end_hub is missing,
                or no path exists between the start and end zones.
        """
        if self.nb_drones == 0:
            raise ParseError(
                "The file must define 'nb_drones: <positive integer>' "
                "as its first meaningful line."
            )
        if self.start_zone is None:
            raise ParseError("The map must define a 'start_hub:'.")
        if self.end_zone is None:
            raise ParseError("The map must define an 'end_hub:'.")
        if not self._is_reachable(self.start_zone, self.end_zone):
            raise ParseError(
                f"No path between '{self.start_zone.name}' and "
                f"'{self.end_zone.name}' (map not connected, or path cut "
                "by 'blocked' zones)."
            )

    def _is_reachable(self, start: Zone, end: Zone) -> bool:
        """Run a depth-first search, ignoring 'blocked' zones.

        Args:
            start: Starting zone.
            end: Destination zone.

        Returns:
            True if at least one path exists from start to end.
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
