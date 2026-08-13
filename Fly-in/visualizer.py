import math
import os
import sys
from typing import Dict, List, Optional, Tuple

import pygame

from design.design_pattern import (
    ACTIVE_LINE_COLOR,
    BG_COLOR,
    DRONE_COLOR,
    LINE_COLOR,
    TEXT_COLOR,
    TYPE_COLORS,
    draw_drone_icon,
    draw_text_with_shadow,
)
from models import Connection, Zone
from window_config import WindowConfig


def run_visualizer(
    zones: Dict[str, Zone],
    connections: List[Connection],
    routes: Dict[str, List[Tuple[str, int]]],
) -> None:
    """Lance le visualiseur pygame de la simulation drone.

    Args:
        zones: Dictionnaire des zones de la carte.
        connections: Liste des connexions entre zones.
        routes: Dictionnaire des chemins calculés par drone.
    """
    pygame.init()

    if not zones:
        print("Aucune zone à afficher.")
        return

    cfg = WindowConfig(zones)
    screen = pygame.display.set_mode((cfg.width, cfg.height))
    pygame.display.set_caption("Fly-in: Advanced Space-Time Visualizer")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("Ubuntu", 13, bold=True)
    title_font = pygame.font.SysFont("Ubuntu", 22, bold=True)

    BG_IMAGE_PATH = "assets/background.jpg"
    bg_image: Optional[pygame.Surface] = None
    if os.path.isfile(BG_IMAGE_PATH):
        try:
            raw_bg = pygame.image.load(BG_IMAGE_PATH).convert()
            bg_image = pygame.transform.scale(raw_bg, (cfg.width, cfg.height))
        except pygame.error as e:
            print(f"Avertissement : impossible de charger le background ({e})")
            bg_image = None

    max_turns = (
        max(
            tour for path in routes.values() for _,
            tour in path
        ) if routes else 0
    )

    current_turn = 0
    is_paused = False
    progress = 0.0
    animation_speed = 0.025

    while True:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    is_paused = not is_paused
                elif event.key == pygame.K_RIGHT or event.key == pygame.K_p:
                    if current_turn < max_turns:
                        current_turn += 1
                        progress = 0.0

        if not is_paused and current_turn < max_turns:
            progress += animation_speed
            if progress >= 1.0:
                progress = 0.0
                current_turn += 1
        elif current_turn >= max_turns:
            progress = 1.0

        if bg_image is not None:
            screen.blit(bg_image, (0, 0))
        else:
            screen.fill(BG_COLOR)

        status_str = "PAUSE" if is_paused else "SIMULATION EN COURS"
        title_str = f"Tour : {current_turn} / {max_turns}  ({status_str})"
        title_w = title_font.size(title_str)[0]
        draw_text_with_shadow(
            screen, title_str, title_font, TEXT_COLOR, (40 + title_w // 2, 36)
        )

        help_str = (
            "[ESPACE] Mettre en Pause/Lecture "
            "| [FLÈCHE DROITE] Forcer le tour suivant"
        )
        help_w = font.size(help_str)[0]
        draw_text_with_shadow(
            screen, help_str, font, TEXT_COLOR, (40 + help_w // 2, 66)
        )

        current_drone_positions: Dict[str, Tuple[int, int]] = {}
        active_links: List[Tuple[str, str]] = []

        for drone_id, path in routes.items():
            pos_now = path[0][0]
            pos_next = path[0][0]

            for zone_name, tour in path:
                if tour <= current_turn:
                    pos_now = zone_name
                if tour <= current_turn + 1:
                    pos_next = zone_name

            pt_now = cfg.to_screen_coords(
                zones[pos_now].x,
                zones[pos_now].y
            )

            pt_next = cfg.to_screen_coords(
                zones[pos_next].x,
                zones[pos_next].y
            )

            interp_x = int(pt_now[0] + (pt_next[0] - pt_now[0]) * progress)
            interp_y = int(pt_now[1] + (pt_next[1] - pt_now[1]) * progress)
            current_drone_positions[drone_id] = (interp_x, interp_y)

            if pos_now != pos_next:
                active_links.append((pos_now, pos_next))

        for conn in connections:
            pt1 = cfg.to_screen_coords(conn.zone1.x, conn.zone1.y)
            pt2 = cfg.to_screen_coords(conn.zone2.x, conn.zone2.y)

            is_active = any(
                (
                    link_a[0] == conn.zone1.name and
                    link_a[1] == conn.zone2.name
                ) or
                (
                    link_a[1] == conn.zone1.name and
                    link_a[0] == conn.zone2.name
                )
                for link_a in active_links
            )

            color = ACTIVE_LINE_COLOR if is_active else LINE_COLOR
            width_line = 3 if is_active else 1
            pygame.draw.line(screen, color, pt1, pt2, width_line)

            mid_x, mid_y = (pt1[0] + pt2[0]) // 2, (pt1[1] + pt2[1]) // 2
            cap_str = f"cap:{conn.max_link_capacity}"
            cap_w = font.size(cap_str)[0]

            draw_text_with_shadow(
                screen,
                cap_str,
                font,
                TEXT_COLOR,
                (mid_x + 6 + cap_w // 2, mid_y - 8)
            )

        for zone in zones.values():
            pos = cfg.to_screen_coords(zone.x, zone.y)
            base_color = TYPE_COLORS.get(zone.zone_type, (140, 140, 140))

            if zone.color:
                try:
                    base_color = pygame.Color(zone.color)
                except ValueError:
                    pass

            pygame.draw.circle(screen, base_color, pos, 22)
            pygame.draw.circle(screen, (255, 255, 255), pos, 22, 2)

            info_str = f"{zone.name} [max:{zone.max_drones}]"
            draw_text_with_shadow(
                screen, info_str, font, TEXT_COLOR, (pos[0], pos[1] - 36)
            )

        drones_at_same_node: Dict[Tuple[int, int], int] = {}
        for drone_id, pos in current_drone_positions.items():
            if progress == 0.0 or progress >= 0.98:
                count = drones_at_same_node.get(pos, 0)
                drones_at_same_node[pos] = count + 1
                if count > 0:
                    angle = count * (2 * math.pi / 4)
                    pos = (
                        int(pos[0] + math.cos(angle) * 15),
                        int(pos[1] + math.sin(angle) * 15),
                    )

            draw_drone_icon(screen, pos, DRONE_COLOR, drone_id, font)

        pygame.display.flip()
