"""
DJI Telemetry Overlay Library

A Python library to parse DJI drone SRT telemetry files and overlay
flight data onto video footage.

Basic usage:
    from dji_telemetry import parse_srt, process_video

    # Parse telemetry
    telemetry = parse_srt('video.SRT')

    # Process video with overlay
    process_video('video.MP4', telemetry, 'output.mp4')

Export telemetry data:
    from dji_telemetry import parse_srt, export

    telemetry = parse_srt('video.SRT')
    export(telemetry, 'telemetry.csv')
    export(telemetry, 'telemetry.json')
    export(telemetry, 'telemetry.gpx')
"""

__version__ = '1.0.0'

# Core parser
from .parser import (
    parse_srt,
    TelemetryFrame,
    TelemetryData,
)

# Exporters
from .exporter import (
    export,
    to_csv,
    to_json,
    to_gpx,
)

# Overlay rendering
from .overlay import (
    OverlayConfig,
    OverlayRenderer,
    create_transparent_frame,
)

# Video processing
from .video import (
    process_video,
    generate_overlay_video,
    generate_overlay_frames,
    add_audio,
    get_video_info,
)

__all__ = [
    # Version
    '__version__',
    # Parser
    'parse_srt',
    'TelemetryFrame',
    'TelemetryData',
    # Exporters
    'export',
    'to_csv',
    'to_json',
    'to_gpx',
    # Overlay
    'OverlayConfig',
    'OverlayRenderer',
    'create_transparent_frame',
    # Video
    'process_video',
    'generate_overlay_video',
    'generate_overlay_frames',
    'add_audio',
    'get_video_info',
]
