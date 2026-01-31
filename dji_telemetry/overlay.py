"""
Telemetry overlay rendering.
"""

import math
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from .parser import TelemetryFrame


@dataclass
class OverlayConfig:
    """Configuration for telemetry overlay rendering."""
    # What to display
    show_altitude: bool = True
    show_speed: bool = True
    show_vertical_speed: bool = True
    show_coordinates: bool = True
    show_camera_settings: bool = True
    show_timestamp: bool = True
    show_speed_gauge: bool = True

    # Speed gauge settings
    gauge_max_speed_kmh: float = 50.0

    # Font settings
    font_scale_factor: float = 1.0

    # Colors (BGR format)
    text_color: tuple[int, int, int] = (255, 255, 255)
    shadow_color: tuple[int, int, int] = (30, 30, 30)
    gauge_color: tuple[int, int, int] = (255, 255, 255)
    gauge_needle_color: tuple[int, int, int] = (255, 200, 0)

    # Position adjustments (relative to video dimensions)
    padding_factor: float = 0.015  # Padding as fraction of height


class OverlayRenderer:
    """Renders telemetry overlay onto video frames."""

    def __init__(self, width: int, height: int, config: Optional[OverlayConfig] = None):
        """
        Initialize the overlay renderer.

        Args:
            width: Video width in pixels
            height: Video height in pixels
            config: Overlay configuration (uses defaults if None)
        """
        self.width = width
        self.height = height
        self.config = config or OverlayConfig()

        # Calculate scaled values
        self.scale_factor = (height / 1080.0) * self.config.font_scale_factor
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale_large = 0.7 * self.scale_factor
        self.font_scale_small = 0.55 * self.scale_factor
        self.thickness = max(1, int(2 * self.scale_factor))
        self.padding = int(height * self.config.padding_factor)
        self.line_height = int(30 * self.scale_factor)

    def _draw_text_with_shadow(
        self,
        img: np.ndarray,
        text: str,
        pos: tuple[int, int],
        font_scale: float,
        color: Optional[tuple[int, int, int]] = None
    ):
        """Draw text with shadow for better visibility."""
        x, y = pos
        color = color or self.config.text_color
        shadow_offset = max(1, int(2 * self.scale_factor))

        cv2.putText(img, text, (x + shadow_offset, y + shadow_offset),
                    self.font, font_scale, self.config.shadow_color,
                    self.thickness + 1, cv2.LINE_AA)
        cv2.putText(img, text, (x, y), self.font, font_scale, color,
                    self.thickness, cv2.LINE_AA)

    def _get_text_size(self, text: str, font_scale: float) -> tuple[int, int]:
        """Get the size of text."""
        size = cv2.getTextSize(text, self.font, font_scale, self.thickness)[0]
        return size[0], size[1]

    def render(self, telemetry: TelemetryFrame, frame: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Render telemetry overlay.

        Args:
            telemetry: Telemetry data for the current frame
            frame: Video frame to draw on (creates transparent if None)

        Returns:
            Frame with telemetry overlay
        """
        if frame is None:
            # Create transparent frame (BGRA)
            overlay = np.zeros((self.height, self.width, 4), dtype=np.uint8)
            is_transparent = True
        else:
            overlay = frame.copy()
            is_transparent = False

        # Get color for drawing (handle transparent vs opaque)
        def get_color(bgr_color):
            if is_transparent:
                return (*bgr_color, 255)  # Add alpha
            return bgr_color

        text_color = get_color(self.config.text_color)
        shadow_color = get_color(self.config.shadow_color)

        # === TOP LEFT: Flight Data ===
        y_pos = self.padding + self.line_height

        if self.config.show_altitude:
            alt_text = f"ALT: {telemetry.rel_alt:.1f}m"
            self._draw_text_with_shadow(overlay, alt_text, (self.padding, y_pos), self.font_scale_large)
            y_pos += self.line_height

        if self.config.show_speed:
            h_speed_kmh = telemetry.h_speed * 3.6
            speed_text = f"H.SPD: {h_speed_kmh:.1f} km/h"
            self._draw_text_with_shadow(overlay, speed_text, (self.padding, y_pos), self.font_scale_large)
            y_pos += self.line_height

        if self.config.show_vertical_speed:
            v_speed_text = f"V.SPD: {telemetry.v_speed:+.1f} m/s"
            self._draw_text_with_shadow(overlay, v_speed_text, (self.padding, y_pos), self.font_scale_large)

        # === TOP RIGHT: Camera Settings ===
        if self.config.show_camera_settings:
            y_pos = self.padding + self.line_height
            right_margin = self.width - self.padding

            # ISO
            iso_text = f"ISO {telemetry.iso}"
            text_w, _ = self._get_text_size(iso_text, self.font_scale_small)
            self._draw_text_with_shadow(overlay, iso_text,
                                        (right_margin - text_w, y_pos), self.font_scale_small)
            y_pos += self.line_height

            # Shutter
            shutter_text = f"{telemetry.shutter}s"
            text_w, _ = self._get_text_size(shutter_text, self.font_scale_small)
            self._draw_text_with_shadow(overlay, shutter_text,
                                        (right_margin - text_w, y_pos), self.font_scale_small)
            y_pos += self.line_height

            # Aperture
            fnum_text = f"f/{telemetry.fnum}"
            text_w, _ = self._get_text_size(fnum_text, self.font_scale_small)
            self._draw_text_with_shadow(overlay, fnum_text,
                                        (right_margin - text_w, y_pos), self.font_scale_small)
            y_pos += self.line_height

            # EV
            ev_text = f"EV {telemetry.ev:+.1f}"
            text_w, _ = self._get_text_size(ev_text, self.font_scale_small)
            self._draw_text_with_shadow(overlay, ev_text,
                                        (right_margin - text_w, y_pos), self.font_scale_small)

        # === BOTTOM LEFT: GPS Coordinates ===
        if self.config.show_coordinates:
            y_pos = self.height - self.padding - self.line_height
            lat_dir = "S" if telemetry.latitude < 0 else "N"
            lon_dir = "W" if telemetry.longitude < 0 else "E"
            coords_text = f"{abs(telemetry.latitude):.6f}{lat_dir}  {abs(telemetry.longitude):.6f}{lon_dir}"
            self._draw_text_with_shadow(overlay, coords_text, (self.padding, y_pos), self.font_scale_small)

        # === BOTTOM RIGHT: Timestamp ===
        if self.config.show_timestamp and telemetry.timestamp:
            time_only = telemetry.timestamp.split(' ')[-1].split('.')[0]  # Get HH:MM:SS
            text_w, _ = self._get_text_size(time_only, self.font_scale_small)
            self._draw_text_with_shadow(overlay, time_only,
                                        (self.width - self.padding - text_w,
                                         self.height - self.padding - self.line_height),
                                        self.font_scale_small)

        # === BOTTOM CENTER: Speed Gauge ===
        if self.config.show_speed_gauge:
            self._draw_speed_gauge(overlay, telemetry.h_speed * 3.6)

        return overlay

    def _draw_speed_gauge(self, img: np.ndarray, speed_kmh: float):
        """Draw the speed gauge at bottom center."""
        gauge_center_x = self.width // 2
        gauge_center_y = self.height - int(80 * self.scale_factor)
        gauge_radius = int(50 * self.scale_factor)

        # Check if transparent (BGRA) or opaque (BGR)
        is_transparent = img.shape[2] == 4

        def get_color(bgr_color):
            if is_transparent:
                return (*bgr_color, 255)
            return bgr_color

        gauge_color = get_color(self.config.gauge_color)
        shadow_color = get_color(self.config.shadow_color)
        needle_color = get_color(self.config.gauge_needle_color)

        # Draw gauge background arc
        cv2.ellipse(img, (gauge_center_x, gauge_center_y), (gauge_radius, gauge_radius),
                    0, 180, 360, shadow_color, max(2, int(4 * self.scale_factor)))
        cv2.ellipse(img, (gauge_center_x, gauge_center_y), (gauge_radius, gauge_radius),
                    0, 180, 360, gauge_color, max(1, int(2 * self.scale_factor)))

        # Speed indicator needle
        speed_ratio = min(speed_kmh / self.config.gauge_max_speed_kmh, 1.0)
        angle_deg = 180 + speed_ratio * 180
        angle_rad = math.radians(angle_deg)

        needle_length = gauge_radius - int(10 * self.scale_factor)
        needle_x = int(gauge_center_x + needle_length * math.cos(angle_rad))
        needle_y = int(gauge_center_y + needle_length * math.sin(angle_rad))

        cv2.line(img, (gauge_center_x, gauge_center_y), (needle_x, needle_y),
                 needle_color, max(2, int(3 * self.scale_factor)), cv2.LINE_AA)

        # Speed value
        speed_val_text = f"{speed_kmh:.0f}"
        text_w, text_h = self._get_text_size(speed_val_text, self.font_scale_large)
        self._draw_text_with_shadow(img, speed_val_text,
                                    (gauge_center_x - text_w // 2,
                                     gauge_center_y - int(10 * self.scale_factor)),
                                    self.font_scale_large)

        # km/h label
        unit_text = "km/h"
        text_w, _ = self._get_text_size(unit_text, self.font_scale_small * 0.8)
        self._draw_text_with_shadow(img, unit_text,
                                    (gauge_center_x - text_w // 2,
                                     gauge_center_y + int(15 * self.scale_factor)),
                                    self.font_scale_small * 0.8)


def create_transparent_frame(width: int, height: int) -> np.ndarray:
    """Create a transparent BGRA frame."""
    return np.zeros((height, width, 4), dtype=np.uint8)
