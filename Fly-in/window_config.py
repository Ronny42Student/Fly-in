from typing import Dict, Tuple

import pygame

from models import Zone


class WindowConfig:
    """Calcule et stocke la configuration
    de la fenêtre pygame selon la carte."""

    MIN_SPACING: int = 200
    PADDING_H: int = 300
    PADDING_V: int = 300
    HEADER_H: int = 150
    DRAW_MARGIN_X: int = 110
    MIN_WIDTH: int = 1000
    MIN_HEIGHT: int = 800

    def __init__(self, zones: Dict[str, Zone]) -> None:
        """Initialise la config depuis les zones de la carte.

        Args:
            zones: Dictionnaire des zones de la carte.
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
        """Calcule la taille optimale de
        la fenêtre selon la dispersion des zones.

        Returns:
            Tuple (width, height) en pixels.
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
        """Convertit des coordonnées carte en coordonnées écran.

        Args:
            x: Coordonnée X dans la carte.
            y: Coordonnée Y dans la carte.

        Returns:
            Tuple (screen_x, screen_y) en pixels.
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
