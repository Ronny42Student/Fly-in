"""Dynamic pygame window sizing and map-to-screen coordinate mapping."""

from typing import Dict, Tuple

import pygame

from models import Zone


class WindowConfig:
    """Computes and stores the pygame window configuration for a given
    map."""

    MIN_SPACING: int = 250
    PADDING_H: int = 200
    PADDING_V: int = 100
    HEADER_H: int = 150
    DRAW_MARGIN_X: int = 100
    MIN_WIDTH: int = 1920
    MIN_HEIGHT: int = 850

    def __init__(self, zones: Dict[str, Zone]) -> None:
        """Initialize the configuration from the map's zones.

        Args:
            zones: Map zones, indexed by name.
        """
        x_coords = [z.x for z in zones.values()]
        y_coords = [z.y for z in zones.values()]

        self.min_x: int = min(x_coords)
        self.max_x: int = max(x_coords)
        self.min_y: int = min(y_coords)
        self.max_y: int = max(y_coords)
        self.range_x: int = max(1, self.max_x - self.min_x)
        self.range_y: int = max(1, self.max_y - self.min_y)

        self.width, self.height = self._compute_size()

        self.draw_margin_y: int = self.HEADER_H + 20
        self.draw_w: int = self.width - self.DRAW_MARGIN_X * 2
        self.draw_h: int = self.height - self.draw_margin_y - 40

    def _compute_size(self) -> Tuple[int, int]:
        """Compute the optimal window size based on how spread out the
        zones are.

        Returns:
            Tuple (width, height) in pixels.
        """
        raw_w = self.range_x * self.MIN_SPACING + self.PADDING_H
        raw_h = (
            self.range_y * self.MIN_SPACING + self.PADDING_V + self.HEADER_H
        )

        info = pygame.display.Info()
        max_w = max(self.MIN_WIDTH, info.current_w - 80)
        max_h = max(self.MIN_HEIGHT, info.current_h - 80)

        width = max(self.MIN_WIDTH, min(int(raw_w), max_w))
        height = max(self.MIN_HEIGHT, min(int(raw_h), max_h))
        return width, height

    def to_screen_coords(self, x: int, y: int) -> Tuple[int, int]:
        """Convert map coordinates into screen coordinates.

        Args:
            x: X coordinate on the map.
            y: Y coordinate on the map.

        Returns:
            Tuple (screen_x, screen_y) in pixels.
        """
        screen_x = int(
            self.DRAW_MARGIN_X + (x - self.min_x) / self.range_x * self.draw_w
        )
        screen_y = int(
            self.draw_margin_y
            + self.draw_h
            - (y - self.min_y) / self.range_y * self.draw_h
        )
        return screen_x, screen_y
