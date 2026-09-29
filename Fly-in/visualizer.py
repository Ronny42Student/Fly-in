"""Pygame-based real-time visualizer for the Fly-in simulation."""

import math
import os
import sys
from typing import Dict, List, Optional, Tuple

import pygame

from design.design_pattern import DesignPattern
from models import Connection, Zone
from window_config import WindowConfig

PathStep = Tuple[str, int, bool]


class Visualizer:
    """Runs the interactive pygame animation of a computed simulation.

    All drones animate simultaneously, in line with the actual
    simulation rules, with interpolated movement between zones,
    active-link highlighting, and pause/step playback controls.
    """

    BG_IMAGE_PATH: str = "assets/background.jpg"
    ANIMATION_SPEED: float = 0.025

    def __init__(
        self,
        zones: Dict[str, Zone],
        connections: List[Connection],
        routes: Dict[str, List[PathStep]],
    ) -> None:
        """Store the map and computed routes to animate.

        Args:
            zones: Map zones, indexed by name.
            connections: Bidirectional connections between zones.
            routes: Per-drone path, as returned by SpaceTimeRouter.
        """
        self.zones = zones
        self.connections = connections
        self.routes = routes

    def run(self) -> None:
        """Open the pygame window and run the animation loop until the
        user closes it."""
        pygame.init()

        if not self.zones:
            print("Aucune zone à afficher.")
            return

        zone_colors = self._resolve_zone_colors()
        cfg = WindowConfig(self.zones)
        screen = pygame.display.set_mode((cfg.width, cfg.height))
        pygame.display.set_caption("Fly-in: Advanced Space-Time Visualizer")
        clock = pygame.time.Clock()

        font = pygame.font.SysFont("Ubuntu", 13, bold=True)
        title_font = pygame.font.SysFont("Ubuntu", 22, bold=True)

        bg_image = self._load_background(cfg)

        zone_routes: Dict[str, List[Tuple[str, int]]] = {
            drone_id: self._zone_steps(path)
            for drone_id, path in self.routes.items()
        }

        max_turns = (
            max(tour for path in zone_routes.values() for _, tour in path)
            if zone_routes else 0
        )

        current_turn = 0
        is_paused = False
        progress = 0.0

        try:
            while True:
                clock.tick(60)

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_SPACE:
                            is_paused = not is_paused
                        elif event.key in (pygame.K_RIGHT, pygame.K_p):
                            if current_turn < max_turns:
                                current_turn += 1
                                progress = 0.0

                if not is_paused and current_turn < max_turns:
                    progress += self.ANIMATION_SPEED
                    if progress >= 1.0:
                        progress = 0.0
                        current_turn += 1
                elif current_turn >= max_turns:
                    progress = 1.0

                if bg_image is not None:
                    screen.blit(bg_image, (0, 0))
                else:
                    screen.fill(DesignPattern.BG_COLOR)

                self._draw_hud(
                    screen, font, title_font, current_turn, max_turns,
                    is_paused,
                )

                positions, active_links, zone_counts = self._compute_frame(
                    cfg, zone_routes, current_turn, progress
                )

                self._draw_connections(screen, cfg, font, active_links)
                self._draw_zones(screen, cfg, font, zone_colors, zone_counts)
                self._draw_drones(screen, font, positions, progress)

                pygame.display.flip()
        finally:
            pygame.quit()

    def _resolve_zone_colors(self) -> Dict[str, Tuple[int, int, int]]:
        """Convert zone colors to RGB before opening the window.

        Zones with no color (or the 'rainbow' keyword) have no entry:
        they are left unfilled (transparent) or drawn separately.

        Returns:
            Dictionary mapping zone name to RGB color.

        Raises:
            ValueError: If a zone has an unknown color.
        """
        resolved: Dict[str, Tuple[int, int, int]] = {}
        for zone in self.zones.values():
            if (
                zone.color is None
                or zone.color == DesignPattern.RAINBOW_KEYWORD
            ):
                continue
            try:
                resolved[zone.name] = DesignPattern.color_to_rgb(zone.color)
            except ValueError as e:
                raise ValueError(f"Zone '{zone.name}' : {e}") from e
        return resolved

    @staticmethod
    def _zone_steps(path: List[PathStep]) -> List[Tuple[str, int]]:
        """Extract only the zone steps of a path (skip connection/transit
        steps)."""
        return [
            (label, tour) for label, tour, is_conn in path if not is_conn
        ]

    def _load_background(
        self, cfg: WindowConfig
    ) -> Optional[pygame.Surface]:
        """Load and scale the optional background image.

        Args:
            cfg: The window configuration, for the target size.

        Returns:
            The scaled background surface, or None if it is unavailable.
        """
        if not os.path.isfile(self.BG_IMAGE_PATH):
            return None
        try:
            raw_bg = pygame.image.load(self.BG_IMAGE_PATH).convert()
            return pygame.transform.scale(raw_bg, (cfg.width, cfg.height))
        except pygame.error as e:
            print(
                f"Avertissement : impossible de charger le background "
                f"({e})"
            )
            return None

    def _draw_hud(
        self,
        screen: pygame.Surface,
        font: pygame.font.Font,
        title_font: pygame.font.Font,
        current_turn: int,
        max_turns: int,
        is_paused: bool,
    ) -> None:
        """Draw the turn counter, status, and help text at the top of
        the screen.

        Args:
            screen: Target pygame surface.
            font: Font used for the help text.
            title_font: Font used for the title.
            current_turn: The simulation turn currently displayed.
            max_turns: Total number of turns in the simulation.
            is_paused: Whether the animation is currently paused.
        """
        status_str = "PAUSE" if is_paused else "SIMULATION EN COURS"
        title_str = f"Tour : {current_turn} / {max_turns}  ({status_str})"
        title_w = title_font.size(title_str)[0]
        DesignPattern.draw_text_with_shadow(
            screen, title_str, title_font, DesignPattern.TEXT_COLOR,
            (1400 + title_w // 2, 36),
        )

        help_str = (
            "[ESPACE] Mettre en Pause/Lecture "
            "| [FLÈCHE DROITE] Forcer le tour suivant"
        )
        help_w = font.size(help_str)[0]
        DesignPattern.draw_text_with_shadow(
            screen, help_str, font, DesignPattern.TEXT_COLOR,
            (1400 + help_w // 2, 66),
        )

    def _compute_frame(
        self,
        cfg: WindowConfig,
        zone_routes: Dict[str, List[Tuple[str, int]]],
        current_turn: int,
        progress: float,
    ) -> Tuple[
        Dict[str, Tuple[int, int]],
        List[Tuple[str, str]],
        Dict[str, int],
    ]:
        """Compute each drone's interpolated screen position for this
        frame, along with the currently active links and zone
        occupancy.

        Args:
            cfg: The window configuration, for coordinate conversion.
            zone_routes: Each drone's zone-only path.
            current_turn: The simulation turn currently displayed.
            progress: Interpolation progress (0.0 to 1.0) toward the
                next turn.

        Returns:
            Tuple (drone screen positions, active links, zone occupancy
            counts).
        """
        positions: Dict[str, Tuple[int, int]] = {}
        active_links: List[Tuple[str, str]] = []
        zone_counts = {z: 0 for z in self.zones}

        for drone_id, path in zone_routes.items():
            pos_now = path[0][0]
            pos_next = path[0][0]

            for zone_name, tour in path:
                if tour <= current_turn:
                    pos_now = zone_name
                if tour <= current_turn + 1:
                    pos_next = zone_name

            pt_now = cfg.to_screen_coords(
                self.zones[pos_now].x, self.zones[pos_now].y
            )
            pt_next = cfg.to_screen_coords(
                self.zones[pos_next].x, self.zones[pos_next].y
            )

            interp_x = int(pt_now[0] + (pt_next[0] - pt_now[0]) * progress)
            interp_y = int(pt_now[1] + (pt_next[1] - pt_now[1]) * progress)
            positions[drone_id] = (interp_x, interp_y)

            if pos_now != pos_next:
                active_links.append((pos_now, pos_next))

            zone_counts[pos_now] += 1

        return positions, active_links, zone_counts

    def _draw_connections(
        self,
        screen: pygame.Surface,
        cfg: WindowConfig,
        font: pygame.font.Font,
        active_links: List[Tuple[str, str]],
    ) -> None:
        """Draw every connection line, highlighting active ones and
        labeling each with its current traffic and capacity.

        Args:
            screen: Target pygame surface.
            cfg: The window configuration, for coordinate conversion.
            font: Font used for the capacity label.
            active_links: Zone-name pairs currently being crossed.
        """
        for conn in self.connections:
            pt1 = cfg.to_screen_coords(conn.zone1.x, conn.zone1.y)
            pt2 = cfg.to_screen_coords(conn.zone2.x, conn.zone2.y)

            is_active = any(
                (a == conn.zone1.name and b == conn.zone2.name)
                or (b == conn.zone1.name and a == conn.zone2.name)
                for a, b in active_links
            )

            color = (
                DesignPattern.ACTIVE_LINE_COLOR if is_active
                else DesignPattern.LINE_COLOR
            )
            width_line = 3 if is_active else 1
            pygame.draw.line(screen, color, pt1, pt2, width_line)

            mid_x = (pt1[0] + pt2[0]) // 2
            mid_y = (pt1[1] + pt2[1]) // 2

            nb = sum(
                1 for a, b in active_links
                if (a == conn.zone1.name and b == conn.zone2.name)
                or (b == conn.zone1.name and a == conn.zone2.name)
            )

            cap_str = f"{nb}/cap:{conn.max_link_capacity}"
            cap_w = font.size(cap_str)[0]

            DesignPattern.draw_text_with_shadow_vertical(
                screen, cap_str, font, DesignPattern.TEXT_COLOR,
                (mid_x + 6 + cap_w // 2, mid_y - 8),
            )

    def _draw_zones(
        self,
        screen: pygame.Surface,
        cfg: WindowConfig,
        font: pygame.font.Font,
        zone_colors: Dict[str, Tuple[int, int, int]],
        zone_counts: Dict[str, int],
    ) -> None:
        """Draw every zone as a colored circle, labeled with its name
        and current/maximum occupancy.

        Args:
            screen: Target pygame surface.
            cfg: The window configuration, for coordinate conversion.
            font: Font used for the zone label.
            zone_colors: RGB color for each zone that has one.
            zone_counts: Current number of drones in each zone.
        """
        for zone in self.zones.values():
            pos = cfg.to_screen_coords(zone.x, zone.y)

            if zone.color == DesignPattern.RAINBOW_KEYWORD:
                DesignPattern.draw_rainbow_circle(screen, pos, 22)
            elif zone.name in zone_colors:
                pygame.draw.circle(screen, zone_colors[zone.name], pos, 22)

            pygame.draw.circle(screen, (255, 255, 255), pos, 22, 2)

            info_str = (
                f"{zone.name} "
                f"[{zone_counts[zone.name]}"
                f"/max:{zone.max_drones}]"
            )

            DesignPattern.draw_text_with_shadow_vertical(
                screen, info_str, font, DesignPattern.TEXT_COLOR,
                (pos[0], pos[1] - 36),
            )

    def _draw_drones(
        self,
        screen: pygame.Surface,
        font: pygame.font.Font,
        positions: Dict[str, Tuple[int, int]],
        progress: float,
    ) -> None:
        """Draw every drone icon, spreading out drones that would
        otherwise overlap so their identifiers stay readable.

        Args:
            screen: Target pygame surface.
            font: Font used for the drone identifier.
            positions: Each drone's interpolated screen position.
            progress: Interpolation progress (0.0 to 1.0); drones are
                only spread apart near the start or end of a turn.
        """
        drones_at_same_node: Dict[Tuple[int, int], int] = {}
        for drone_id, pos in positions.items():
            if progress == 0.0 or progress >= 0.98:
                count = drones_at_same_node.get(pos, 0)
                drones_at_same_node[pos] = count + 1
                if count > 0:
                    angle = count * (2 * math.pi / 4)
                    pos = (
                        int(pos[0] + math.cos(angle) * 15),
                        int(pos[1] + math.sin(angle) * 15),
                    )

            DesignPattern.draw_drone_icon(
                screen, pos, DesignPattern.DRONE_COLOR, drone_id, font
            )
