import os
from typing import Optional

import pygame

from models import ZoneType

BG_COLOR = (135, 170, 210)

LINE_COLOR = (10, 20, 60)
ACTIVE_LINE_COLOR = (255, 220, 0)

TEXT_COLOR = (5, 10, 40)

DRONE_COLOR = (255, 100, 0)

TYPE_COLORS = {
    ZoneType.NORMAL: (20, 60, 180),
    ZoneType.BLOCKED: (180, 0, 30),
    ZoneType.RESTRICTED: (200, 80, 0),
    ZoneType.PRIORITY: (0, 140, 60),
}


def draw_text_with_shadow(
    screen: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    color: tuple[int, int, int],
    center: tuple[int, int],
) -> None:
    """Dessine un texte avec ombre portée pour lisibilité sur fond photo.

    Args:
        screen: Surface pygame cible.
        text: Texte à afficher.
        font: Police pygame.
        color: Couleur du texte principal.
        center: Position centrale (x, y) en pixels.
    """
    shadow_color: tuple[int, int, int] = (220, 230, 255)
    shadow_surf = font.render(text, True, shadow_color)
    shadow_rect = shadow_surf.get_rect(center=(center[0] + 1, center[1] + 1))
    screen.blit(shadow_surf, shadow_rect)

    text_surf = font.render(text, True, color)
    text_rect = text_surf.get_rect(center=center)
    screen.blit(text_surf, text_rect)


DRONE_IMAGE_PATH = "assets/drone.png"
DRONE_IMAGE_SIZE = 100

_drone_image_cache: dict[int, Optional[pygame.Surface]] = {}


def _load_drone_image(size: int) -> Optional[pygame.Surface]:
    """Charge et met en cache l'image PNG du drone, redimensionnée.

    Args:
        size: Taille cible en pixels (carré).

    Returns:
        Surface pygame prête à l'emploi,
        ou None si le fichier est absent/invalide.
    """
    if size in _drone_image_cache:
        return _drone_image_cache[size]

    surface: Optional[pygame.Surface] = None
    if os.path.isfile(DRONE_IMAGE_PATH):
        try:
            raw = pygame.image.load(DRONE_IMAGE_PATH).convert_alpha()
            surface = pygame.transform.smoothscale(raw, (size, size))
        except pygame.error:
            surface = None

    _drone_image_cache[size] = surface
    return surface


def draw_drone_icon(
    screen: pygame.Surface,
    center: tuple[int, int],
    color: tuple[int, int, int],
    drone_id: str,
    font: pygame.font.Font,
) -> None:
    """Dessine le drone depuis un PNG (assets/drone.png)
    ou en vectoriel si le fichier est absent.

    L'image PNG est chargée une seule fois puis mise en cache.
    Le numéro du drone est toujours affiché par-dessus.

    Args:
        screen: Surface pygame cible.
        center: Position centrale (x, y) en pixels.
        color: Couleur de fallback (utilisée si le PNG est absent).
        drone_id: Identifiant du drone (ex: 'd1').
        font: Police pour l'identifiant.
    """
    x, y = center
    img = _load_drone_image(DRONE_IMAGE_SIZE)

    if img is not None:
        rect = img.get_rect(center=(x, y))
        screen.blit(img, rect)
    else:
        size = 14
        arm_color: tuple[int, int, int] = (240, 245, 255)
        arm_shadow: tuple[int, int, int] = (10, 20, 60)

        for offset in range(2, 0, -1):
            pygame.draw.line(
                screen,
                arm_shadow,
                (x - size - offset, y - size - offset),
                (x + size + offset, y + size + offset),
                4,
            )
            pygame.draw.line(
                screen,
                arm_shadow,
                (x - size - offset, y + size + offset),
                (x + size + offset, y - size - offset),
                4,
            )

        pygame.draw.line(
            screen, arm_color, (x - size, y - size), (x + size, y + size), 3
        )
        pygame.draw.line(
            screen, arm_color, (x - size, y + size), (x + size, y - size), 3
        )

        motor_fill: tuple[int, int, int] = (200, 210, 230)
        motor_border: tuple[int, int, int] = (10, 20, 60)
        motor_positions = [
            (-size, -size), (size, -size), (-size, size), (size, size)
        ]
        for dx, dy in motor_positions:
            pygame.draw.circle(screen, motor_border, (x + dx, y + dy), 5)
            pygame.draw.circle(screen, motor_fill, (x + dx, y + dy), 4)

        pygame.draw.circle(screen, arm_shadow, (x, y), 10)
        pygame.draw.circle(screen, color, (x, y), 8)
        pygame.draw.circle(screen, (255, 255, 255), (x, y), 8, 1)

    draw_text_with_shadow(screen, drone_id[1:], font, (0, 0, 0), (x, y))
