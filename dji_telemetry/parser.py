"""
DJI SRT telemetry file parser.
"""

import re
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class TelemetryFrame:
    """Telemetry data for a single frame."""
    frame_num: int
    start_time_ms: float
    end_time_ms: float
    timestamp: str
    iso: int
    shutter: str
    fnum: float
    ev: float
    ct: int  # color temperature
    latitude: float
    longitude: float
    rel_alt: float  # relative altitude
    abs_alt: float  # absolute altitude
    # Calculated fields
    h_speed: float = 0.0  # horizontal speed (m/s)
    v_speed: float = 0.0  # vertical speed (m/s)
    distance: float = 0.0  # cumulative distance traveled (m)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'frame_num': self.frame_num,
            'start_time_ms': self.start_time_ms,
            'end_time_ms': self.end_time_ms,
            'timestamp': self.timestamp,
            'iso': self.iso,
            'shutter': self.shutter,
            'fnum': self.fnum,
            'ev': self.ev,
            'color_temp': self.ct,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'rel_altitude_m': self.rel_alt,
            'abs_altitude_m': self.abs_alt,
            'h_speed_ms': self.h_speed,
            'v_speed_ms': self.v_speed,
            'h_speed_kmh': self.h_speed * 3.6,
            'distance_m': self.distance,
        }


@dataclass
class TelemetryData:
    """Container for all telemetry data from an SRT file."""
    frames: list[TelemetryFrame] = field(default_factory=list)
    source_file: Optional[str] = None

    @property
    def duration_seconds(self) -> float:
        """Total duration in seconds."""
        if not self.frames:
            return 0.0
        return self.frames[-1].end_time_ms / 1000.0

    @property
    def total_distance(self) -> float:
        """Total distance traveled in meters."""
        if not self.frames:
            return 0.0
        return self.frames[-1].distance

    @property
    def max_altitude(self) -> float:
        """Maximum relative altitude in meters."""
        if not self.frames:
            return 0.0
        return max(f.rel_alt for f in self.frames)

    @property
    def max_speed(self) -> float:
        """Maximum horizontal speed in m/s."""
        if not self.frames:
            return 0.0
        return max(f.h_speed for f in self.frames)

    @property
    def start_coordinates(self) -> tuple[float, float]:
        """Starting coordinates (lat, lon)."""
        if not self.frames:
            return (0.0, 0.0)
        return (self.frames[0].latitude, self.frames[0].longitude)

    @property
    def end_coordinates(self) -> tuple[float, float]:
        """Ending coordinates (lat, lon)."""
        if not self.frames:
            return (0.0, 0.0)
        return (self.frames[-1].latitude, self.frames[-1].longitude)

    def get_frame_at_time(self, time_ms: float) -> Optional[TelemetryFrame]:
        """Find the telemetry frame for a given video time."""
        for frame in self.frames:
            if frame.start_time_ms <= time_ms < frame.end_time_ms:
                return frame

        if self.frames:
            if time_ms < self.frames[0].start_time_ms:
                return self.frames[0]
            if time_ms >= self.frames[-1].end_time_ms:
                return self.frames[-1]

        return None

    def to_list(self) -> list[dict]:
        """Convert all frames to list of dictionaries."""
        return [f.to_dict() for f in self.frames]


def _parse_time_to_ms(time_str: str) -> float:
    """Convert SRT time format (HH:MM:SS,mmm) to milliseconds."""
    match = re.match(r"(\d+):(\d+):(\d+),(\d+)", time_str)
    if match:
        h, m, s, ms = map(int, match.groups())
        return (h * 3600 + m * 60 + s) * 1000 + ms
    return 0.0


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two GPS coordinates in meters."""
    R = 6371000  # Earth's radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def parse_srt(srt_path: str | Path, smooth_speeds: bool = True, window_size: int = 15) -> TelemetryData:
    """
    Parse a DJI SRT file and extract telemetry data.

    Args:
        srt_path: Path to the SRT file
        smooth_speeds: Apply moving average smoothing to speed calculations
        window_size: Window size for speed smoothing

    Returns:
        TelemetryData object containing all frames
    """
    srt_path = Path(srt_path)
    frames = []

    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split into subtitle blocks
    blocks = re.split(r'\n\n+', content.strip())

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue

        # Parse frame number
        try:
            frame_num = int(lines[0])
        except ValueError:
            continue

        # Parse time range
        time_match = re.match(r"(\d+:\d+:\d+,\d+)\s*-->\s*(\d+:\d+:\d+,\d+)", lines[1])
        if not time_match:
            continue

        start_time = _parse_time_to_ms(time_match.group(1))
        end_time = _parse_time_to_ms(time_match.group(2))

        # Join remaining lines for metadata
        metadata_text = ' '.join(lines[2:])

        # Remove font tags
        metadata_text = re.sub(r'<[^>]+>', '', metadata_text)

        # Extract timestamp
        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)', metadata_text)
        timestamp = timestamp_match.group(1) if timestamp_match else ""

        # Extract values using regex
        def extract_value(pattern: str, default=0):
            match = re.search(pattern, metadata_text)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    return default
            return default

        def extract_str(pattern: str, default=""):
            match = re.search(pattern, metadata_text)
            return match.group(1) if match else default

        frame = TelemetryFrame(
            frame_num=frame_num,
            start_time_ms=start_time,
            end_time_ms=end_time,
            timestamp=timestamp,
            iso=int(extract_value(r'\[iso:\s*(\d+)\]')),
            shutter=extract_str(r'\[shutter:\s*([^\]]+)\]'),
            fnum=extract_value(r'\[fnum:\s*([\d.]+)\]'),
            ev=extract_value(r'\[ev:\s*([+-]?[\d.]+)\]'),
            ct=int(extract_value(r'\[ct:\s*(\d+)\]')),
            latitude=extract_value(r'\[latitude:\s*([+-]?[\d.]+)\]'),
            longitude=extract_value(r'\[longitude:\s*([+-]?[\d.]+)\]'),
            rel_alt=extract_value(r'\[rel_alt:\s*([\d.]+)'),
            abs_alt=extract_value(r'\[abs_alt:\s*([\d.]+)'),
        )

        frames.append(frame)

    # Sort by frame number
    frames.sort(key=lambda f: f.frame_num)

    # Calculate speeds and cumulative distance
    cumulative_distance = 0.0
    for i in range(1, len(frames)):
        prev = frames[i - 1]
        curr = frames[i]

        # Time delta in seconds
        dt = (curr.start_time_ms - prev.start_time_ms) / 1000.0
        if dt <= 0:
            dt = 0.033  # ~30fps fallback

        # Horizontal distance from GPS coordinates
        h_dist = _haversine_distance(prev.latitude, prev.longitude,
                                      curr.latitude, curr.longitude)
        curr.h_speed = h_dist / dt
        cumulative_distance += h_dist
        curr.distance = cumulative_distance

        # Vertical speed from altitude change
        v_dist = curr.rel_alt - prev.rel_alt
        curr.v_speed = v_dist / dt

    # Apply speed smoothing
    if smooth_speeds and len(frames) > window_size:
        h_speeds = [f.h_speed for f in frames]
        v_speeds = [f.v_speed for f in frames]

        for i in range(len(frames)):
            start_idx = max(0, i - window_size // 2)
            end_idx = min(len(frames), i + window_size // 2 + 1)

            frames[i].h_speed = sum(h_speeds[start_idx:end_idx]) / (end_idx - start_idx)
            frames[i].v_speed = sum(v_speeds[start_idx:end_idx]) / (end_idx - start_idx)

    return TelemetryData(frames=frames, source_file=str(srt_path))
