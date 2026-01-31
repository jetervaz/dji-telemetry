# DJI Telemetry

A Python library to parse DJI drone SRT telemetry files, export flight data, and overlay telemetry onto video footage.

Tested with **DJI Neo 2** but should work with other DJI drones that generate SRT telemetry files.

## Features

- **Parse** DJI SRT telemetry files (per-frame metadata)
- **Calculate** horizontal/vertical speeds from GPS data
- **Export** to CSV, JSON, or GPX formats
- **Overlay** telemetry data onto video footage
- **Generate** transparent overlay videos or frame sequences

## Installation

```bash
pip install dji-telemetry
```

Or install from source:

```bash
git clone https://github.com/jetervaz/dji-telemetry.git
cd dji-telemetry
pip install -e .
```

## Quick Start

### Python Library

```python
from dji_telemetry import parse_srt, process_video, export

# Parse telemetry data
telemetry = parse_srt('flight.SRT')

# Show flight stats
print(f"Duration: {telemetry.duration_seconds:.1f}s")
print(f"Distance: {telemetry.total_distance:.1f}m")
print(f"Max altitude: {telemetry.max_altitude:.1f}m")
print(f"Max speed: {telemetry.max_speed * 3.6:.1f} km/h")

# Export to different formats
export(telemetry, 'flight.csv')
export(telemetry, 'flight.json')
export(telemetry, 'flight.gpx')

# Process video with overlay
process_video('flight.MP4', telemetry, 'flight_with_telemetry.mp4')
```

### Command Line

```bash
# Process video with telemetry overlay
dji-telemetry overlay video.MP4 --audio

# Generate transparent overlay video (for compositing)
dji-telemetry overlay-only video.SRT -o overlay.mp4 --width 3840 --height 2160

# Generate PNG frame sequence (for video editors)
dji-telemetry frames video.SRT -o frames/ --width 1920 --height 1080

# Export telemetry data
dji-telemetry export video.SRT -o telemetry.csv
dji-telemetry export video.SRT -o telemetry.json
dji-telemetry export video.SRT -o flight.gpx

# Show file information
dji-telemetry info video.SRT
dji-telemetry info video.MP4
```

## API Reference

### Parsing

```python
from dji_telemetry import parse_srt, TelemetryData, TelemetryFrame

# Parse SRT file
telemetry: TelemetryData = parse_srt('flight.SRT')

# Access frames
for frame in telemetry.frames:
    print(f"Alt: {frame.rel_alt}m, Speed: {frame.h_speed * 3.6:.1f} km/h")

# Get frame at specific time
frame = telemetry.get_frame_at_time(5000)  # 5 seconds

# Flight statistics
telemetry.duration_seconds
telemetry.total_distance
telemetry.max_altitude
telemetry.max_speed
telemetry.start_coordinates
telemetry.end_coordinates
```

### Exporting

```python
from dji_telemetry import parse_srt, export, to_csv, to_json, to_gpx

telemetry = parse_srt('flight.SRT')

# Auto-detect format from extension
export(telemetry, 'data.csv')
export(telemetry, 'data.json')
export(telemetry, 'track.gpx')

# Or use specific exporters
to_csv(telemetry, 'data.csv', include_all_fields=True)
to_json(telemetry, 'data.json', indent=2)
to_gpx(telemetry, 'track.gpx', name='My Flight')
```

### Video Processing

```python
from dji_telemetry import (
    parse_srt,
    process_video,
    generate_overlay_video,
    generate_overlay_frames,
    add_audio,
    OverlayConfig
)

telemetry = parse_srt('flight.SRT')

# Custom overlay configuration
config = OverlayConfig(
    show_altitude=True,
    show_speed=True,
    show_vertical_speed=True,
    show_coordinates=True,
    show_camera_settings=True,
    show_timestamp=True,
    show_speed_gauge=True,
    gauge_max_speed_kmh=60.0,
)

# Process video with overlay
process_video(
    'flight.MP4',
    telemetry,
    'output.mp4',
    config=config,
    progress_callback=lambda cur, total: print(f"{cur}/{total}")
)

# Add audio from original
add_audio('output.mp4', 'flight.MP4', 'output_with_audio.mp4')

# Generate overlay-only video (black background, for compositing)
generate_overlay_video(
    telemetry,
    'overlay.mp4',
    width=3840,
    height=2160,
    fps=30.0,
    config=config
)

# Generate PNG frame sequence (with transparency)
generate_overlay_frames(
    telemetry,
    'frames/',
    width=1920,
    height=1080,
    fps=30.0,
    format='png'
)
```

### Overlay Configuration

```python
from dji_telemetry import OverlayConfig

config = OverlayConfig(
    # Toggle elements
    show_altitude=True,
    show_speed=True,
    show_vertical_speed=True,
    show_coordinates=True,
    show_camera_settings=True,
    show_timestamp=True,
    show_speed_gauge=True,

    # Speed gauge
    gauge_max_speed_kmh=50.0,

    # Styling
    font_scale_factor=1.0,
    text_color=(255, 255, 255),      # BGR: White
    shadow_color=(30, 30, 30),       # BGR: Dark gray
    gauge_color=(255, 255, 255),     # BGR: White
    gauge_needle_color=(255, 200, 0), # BGR: Orange
)
```

## Overlay Layout

The default overlay displays:

```
┌─────────────────────────────────────────────────────────────┐
│ ALT: 57.2m                                        ISO 100   │
│ H.SPD: 12.5 km/h                                1/1250.0s   │
│ V.SPD: +1.2 m/s                                     f/2.2   │
│                                                   EV -1.3   │
│                                                             │
│                                                             │
│                                                             │
│                                                             │
│                          ┌───┐                              │
│                          │ 12│                              │
│                          │kmh│                              │
│                          └───┘                              │
│ 29.685883S  53.777843W                           09:58:21   │
└─────────────────────────────────────────────────────────────┘
```

## DJI SRT Format

DJI drones generate SRT files with per-frame telemetry:

```
1
00:00:00,000 --> 00:00:00,033
<font size="28">FrameCnt: 1, DiffTime: 33ms
2026-01-30 09:58:21.637
[iso: 100] [shutter: 1/1250.0] [fnum: 2.2] [ev: -1.3] [ct: 6700]
[latitude: -29.685883] [longitude: -53.777843]
[rel_alt: 57.200 abs_alt: 204.644] ...</font>
```

### Supported Fields

| Field | Description |
|-------|-------------|
| `iso` | ISO sensitivity |
| `shutter` | Shutter speed |
| `fnum` | Aperture (f-number) |
| `ev` | Exposure compensation |
| `ct` | Color temperature (Kelvin) |
| `latitude` | GPS latitude |
| `longitude` | GPS longitude |
| `rel_alt` | Relative altitude (from takeoff) |
| `abs_alt` | Absolute altitude (sea level) |

### Calculated Fields

| Field | Description |
|-------|-------------|
| `h_speed` | Horizontal speed (calculated from GPS) |
| `v_speed` | Vertical speed (calculated from altitude) |
| `distance` | Cumulative distance traveled |

## License

This project is licensed under the [MIT License](LICENSE).
