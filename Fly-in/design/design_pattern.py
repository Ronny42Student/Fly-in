"""Colors and pygame drawing helpers shared by the parser and the
visualizer."""

import math
import os
from typing import Dict, List, Optional, Tuple

import pygame

from models import ZoneType


class DesignPattern:
    """Namespace class for shared colors, color parsing, and drawing
    helpers.

    Grouping these as static/class methods (rather than loose module
    functions) is what lets the parser and the visualizer share a
    single, object-oriented source of truth for color validation and
    drawing, in line with the subject's "completely object-oriented"
    constraint.
    """

    RAINBOW_COLORS: List[Tuple[int, int, int]] = [
        (255, 0, 0), (255, 127, 0), (255, 255, 0),
        (0, 255, 0), (0, 0, 255), (75, 0, 130), (148, 0, 211),
    ]

    RAINBOW_KEYWORD: str = "rainbow"

    BG_COLOR: Tuple[int, int, int] = (135, 170, 210)

    LINE_COLOR: Tuple[int, int, int] = (10, 20, 60)
    ACTIVE_LINE_COLOR: Tuple[int, int, int] = (255, 220, 0)

    TEXT_COLOR: Tuple[int, int, int] = (5, 10, 40)

    DRONE_COLOR: Tuple[int, int, int] = (255, 100, 0)

    TYPE_COLORS: Dict[ZoneType, Tuple[int, int, int]] = {
        ZoneType.NORMAL: (20, 60, 180),
        ZoneType.BLOCKED: (180, 0, 30),
        ZoneType.RESTRICTED: (200, 80, 0),
        ZoneType.PRIORITY: (0, 140, 60),
    }

    DRONE_IMAGE_PATH: str = "assets/drone.png"
    DRONE_IMAGE_SIZE: int = 100

    _drone_image_cache: Dict[int, Optional[pygame.Surface]] = {}

    @staticmethod
    def color_to_rgb(name: str) -> Tuple[int, int, int]:
        """Convert a map-file color name into an RGB tuple.

        This is the single source of color validation: both the parser
        and the visualizer use it, so they always agree on what counts
        as a valid color. Accepts pygame color names (red, lightblue,
        ...) and hex codes (#ff0000). The 'rainbow' keyword is not an
        RGB color and must be handled separately (see RAINBOW_KEYWORD).

        Args:
            name: The color name as written in the map file.

        Returns:
            Tuple (r, g, b).

        Raises:
            ValueError: If the color is unknown to pygame.
        """
        try:
            color = pygame.Color(name)
        except (ValueError, TypeError):
            raise ValueError(f"Couleur invalide : '{name}'") from None
        return (color.r, color.g, color.b)

    @staticmethod
    def draw_text_with_shadow_vertical(
        screen: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        color: Tuple[int, int, int],
        center: Tuple[int, int],
    ) -> None:
        """Draw vertical (90°-rotated) text with a drop shadow, for
        readability over a photo background.

        Args:
            screen: Target pygame surface.
            text: Text to display.
            font: Pygame font.
            color: Main text color.
            center: Center position (x, y) in pixels.
        """
        shadow_color: Tuple[int, int, int] = (220, 230, 255)
        shadow_surf = font.render(text, True, shadow_color)
        shadow_surf = pygame.transform.rotate(shadow_surf, 90)
        shadow_rect = shadow_surf.get_rect(
            center=(center[0] + 1, center[1] + 1)
        )
        screen.blit(shadow_surf, shadow_rect)

        text_surf = font.render(text, True, color)
        text_surf = pygame.transform.rotate(text_surf, 90)
        text_rect = text_surf.get_rect(center=center)
        screen.blit(text_surf, text_rect)

    @staticmethod
    def draw_text_with_shadow(
        screen: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        color: Tuple[int, int, int],
        center: Tuple[int, int],
    ) -> None:
        """Draw horizontal text with a drop shadow, for readability over
        a photo background.

        Args:
            screen: Target pygame surface.
            text: Text to display.
            font: Pygame font.
            color: Main text color.
            center: Center position (x, y) in pixels.
        """
        shadow_color: Tuple[int, int, int] = (220, 230, 255)
        shadow_surf = font.render(text, True, shadow_color)
        shadow_rect = shadow_surf.get_rect(
            center=(center[0] + 1, center[1] + 1)
        )
        screen.blit(shadow_surf, shadow_rect)

        text_surf = font.render(text, True, color)
        text_rect = text_surf.get_rect(center=center)
        screen.blit(text_surf, text_rect)

    @classmethod
    def _load_drone_image(cls, size: int) -> Optional[pygame.Surface]:
        """Load and cache the drone PNG image, resized to `size`.

        Args:
            size: Target size in pixels (the image is square).

        Returns:
            A ready-to-use pygame surface, or None if the file is
            missing or invalid.
        """
        if size in cls._drone_image_cache:
            return cls._drone_image_cache[size]

        surface: Optional[pygame.Surface] = None
        if os.path.isfile(cls.DRONE_IMAGE_PATH):
            try:
                raw = pygame.image.load(cls.DRONE_IMAGE_PATH).convert_alpha()
                surface = pygame.transform.smoothscale(raw, (size, size))
            except pygame.error:
                surface = None

        cls._drone_image_cache[size] = surface
        return surface

    @classmethod
    def draw_drone_icon(
        cls,
        screen: pygame.Surface,
        center: Tuple[int, int],
        color: Tuple[int, int, int],
        drone_id: str,
        font: pygame.font.Font,
    ) -> None:
        """Draw a drone, from a PNG (assets/drone.png) if available, or
        as a small vector icon otherwise.

        The PNG is loaded once and then cached. The drone's numeric
        identifier is always drawn on top of the icon.

        Args:
            screen: Target pygame surface.
            center: Center position (x, y) in pixels.
            color: Fallback color, used only if the PNG is missing.
            drone_id: Drone identifier (e.g. 'd1').
            font: Font used to render the identifier.
        """
        x, y = center
        img = cls._load_drone_image(cls.DRONE_IMAGE_SIZE)

        if img is not None:
            rect = img.get_rect(center=(x, y))
            screen.blit(img, rect)
        else:
            size = 14
            arm_color: Tuple[int, int, int] = (240, 245, 255)
            arm_shadow: Tuple[int, int, int] = (10, 20, 60)

            for offset in range(2, 0, -1):
                pygame.draw.line(
                    screen, arm_shadow,
                    (x - size - offset, y - size - offset),
                    (x + size + offset, y + size + offset), 4,
                )
                pygame.draw.line(
                    screen, arm_shadow,
                    (x - size - offset, y + size + offset),
                    (x + size + offset, y - size - offset), 4,
                )

            pygame.draw.line(
                screen, arm_color,
                (x - size, y - size), (x + size, y + size), 3,
            )
            pygame.draw.line(
                screen, arm_color,
                (x - size, y + size), (x + size, y - size), 3,
            )

            motor_fill: Tuple[int, int, int] = (200, 210, 230)
            motor_border: Tuple[int, int, int] = (10, 20, 60)
            motor_positions = [
                (-size, -size), (size, -size), (-size, size), (size, size)
            ]
            for dx, dy in motor_positions:
                pygame.draw.circle(screen, motor_border, (x + dx, y + dy), 5)
                pygame.draw.circle(screen, motor_fill, (x + dx, y + dy), 4)

            pygame.draw.circle(screen, arm_shadow, (x, y), 10)
            pygame.draw.circle(screen, color, (x, y), 8)
            pygame.draw.circle(screen, (255, 255, 255), (x, y), 8, 1)

        cls.draw_text_with_shadow_vertical(
            screen, drone_id[1:], font, (0, 0, 0), (x, y)
        )

    @staticmethod
    def draw_rainbow_circle(
        screen: pygame.Surface,
        center: Tuple[int, int],
        radius: int,
    ) -> None:
        """Draw a circle filled with a rainbow gradient (colored
        sectors), used for the special 'rainbow' zone color.

        Args:
            screen: Target pygame surface.
            center: Center position (x, y) in pixels.
            radius: Circle radius in pixels.
        """
        x, y = center
        n = len(DesignPattern.RAINBOW_COLORS)
        for i, color in enumerate(DesignPattern.RAINBOW_COLORS):
            start_angle = (2 * math.pi / n) * i
            end_angle = (2 * math.pi / n) * (i + 1)
            points: List[Tuple[int, int]] = [(x, y)]
            steps = 10
            for s in range(steps + 1):
                angle = start_angle + (end_angle - start_angle) * s / steps
                points.append(
                    (
                        int(x + radius * math.cos(angle)),
                        int(y + radius * math.sin(angle)),
                    )
                )
            pygame.draw.polygon(screen, color, points)
