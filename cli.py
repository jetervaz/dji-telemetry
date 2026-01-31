#!/usr/bin/env python3
"""
DJI Telemetry Overlay - Command Line Interface
"""

import argparse
import sys
from pathlib import Path

from dji_telemetry import (
    __version__,
    parse_srt,
    export,
    process_video,
    generate_overlay_video,
    generate_overlay_frames,
    add_audio,
    get_video_info,
    OverlayConfig,
)


def progress_bar(current: int, total: int, width: int = 50):
    """Display a progress bar."""
    percent = current / total
    filled = int(width * percent)
    bar = '=' * filled + '-' * (width - filled)
    sys.stdout.write(f'\r[{bar}] {percent*100:.1f}% ({current}/{total})')
    sys.stdout.flush()
    if current == total:
        print()


def cmd_overlay(args):
    """Process video with telemetry overlay."""
    video_path = Path(args.video)
    srt_path = Path(args.srt) if args.srt else video_path.with_suffix('.SRT')

    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}")
        return 1

    if not srt_path.exists():
        print(f"Error: SRT file not found: {srt_path}")
        return 1

    output_path = Path(args.output) if args.output else video_path.with_name(
        video_path.stem + '_telemetry.mp4'
    )

    print(f"Parsing telemetry: {srt_path}")
    telemetry = parse_srt(srt_path)
    print(f"  Loaded {len(telemetry.frames)} frames")
    print(f"  Duration: {telemetry.duration_seconds:.1f}s")
    print(f"  Max altitude: {telemetry.max_altitude:.1f}m")
    print(f"  Max speed: {telemetry.max_speed * 3.6:.1f} km/h")

    # Build overlay config
    config = OverlayConfig(
        show_altitude=not args.no_altitude,
        show_speed=not args.no_speed,
        show_vertical_speed=not args.no_vspeed,
        show_coordinates=not args.no_coords,
        show_camera_settings=not args.no_camera,
        show_timestamp=not args.no_timestamp,
        show_speed_gauge=not args.no_gauge,
        gauge_max_speed_kmh=args.gauge_max,
    )

    print(f"\nProcessing video: {video_path}")
    temp_output = output_path.with_name(output_path.stem + '_temp.mp4')

    process_video(
        video_path, telemetry, temp_output, config,
        progress_callback=progress_bar if not args.quiet else None
    )

    # Add audio if requested
    if args.audio:
        print(f"Adding audio from: {video_path}")
        add_audio(temp_output, video_path, output_path)
        temp_output.unlink()
    else:
        temp_output.rename(output_path)

    print(f"\nOutput saved to: {output_path}")
    return 0


def cmd_overlay_only(args):
    """Generate transparent overlay video."""
    srt_path = Path(args.srt)

    if not srt_path.exists():
        print(f"Error: SRT file not found: {srt_path}")
        return 1

    output_path = Path(args.output) if args.output else srt_path.with_name(
        srt_path.stem + '_overlay.mp4'
    )

    print(f"Parsing telemetry: {srt_path}")
    telemetry = parse_srt(srt_path)
    print(f"  Loaded {len(telemetry.frames)} frames")

    config = OverlayConfig(
        show_altitude=not args.no_altitude,
        show_speed=not args.no_speed,
        show_vertical_speed=not args.no_vspeed,
        show_coordinates=not args.no_coords,
        show_camera_settings=not args.no_camera,
        show_timestamp=not args.no_timestamp,
        show_speed_gauge=not args.no_gauge,
        gauge_max_speed_kmh=args.gauge_max,
    )

    print(f"\nGenerating overlay video: {args.width}x{args.height} @ {args.fps}fps")
    generate_overlay_video(
        telemetry, output_path,
        width=args.width, height=args.height, fps=args.fps,
        config=config,
        progress_callback=progress_bar if not args.quiet else None
    )

    print(f"\nOutput saved to: {output_path}")
    return 0


def cmd_frames(args):
    """Generate transparent overlay frames."""
    srt_path = Path(args.srt)

    if not srt_path.exists():
        print(f"Error: SRT file not found: {srt_path}")
        return 1

    output_dir = Path(args.output) if args.output else srt_path.with_name(
        srt_path.stem + '_frames'
    )

    print(f"Parsing telemetry: {srt_path}")
    telemetry = parse_srt(srt_path)
    print(f"  Loaded {len(telemetry.frames)} frames")

    config = OverlayConfig(
        show_altitude=not args.no_altitude,
        show_speed=not args.no_speed,
        show_vertical_speed=not args.no_vspeed,
        show_coordinates=not args.no_coords,
        show_camera_settings=not args.no_camera,
        show_timestamp=not args.no_timestamp,
        show_speed_gauge=not args.no_gauge,
    )

    print(f"\nGenerating frames: {args.width}x{args.height} @ {args.fps}fps")
    generate_overlay_frames(
        telemetry, output_dir,
        width=args.width, height=args.height, fps=args.fps,
        config=config, format=args.format,
        progress_callback=progress_bar if not args.quiet else None
    )

    print(f"\nFrames saved to: {output_dir}")
    return 0


def cmd_export(args):
    """Export telemetry data to CSV, JSON, or GPX."""
    srt_path = Path(args.srt)

    if not srt_path.exists():
        print(f"Error: SRT file not found: {srt_path}")
        return 1

    output_path = Path(args.output)

    print(f"Parsing telemetry: {srt_path}")
    telemetry = parse_srt(srt_path)
    print(f"  Loaded {len(telemetry.frames)} frames")
    print(f"  Duration: {telemetry.duration_seconds:.1f}s")
    print(f"  Distance: {telemetry.total_distance:.1f}m")

    print(f"\nExporting to: {output_path}")
    export(telemetry, output_path, format=args.format)

    print("Done!")
    return 0


def cmd_info(args):
    """Show information about video and SRT files."""
    path = Path(args.path)

    if not path.exists():
        print(f"Error: File not found: {path}")
        return 1

    if path.suffix.upper() == '.SRT':
        print(f"SRT File: {path}")
        print("-" * 50)
        telemetry = parse_srt(path)
        print(f"Frames:        {len(telemetry.frames)}")
        print(f"Duration:      {telemetry.duration_seconds:.1f}s")
        print(f"Distance:      {telemetry.total_distance:.1f}m")
        print(f"Max altitude:  {telemetry.max_altitude:.1f}m")
        print(f"Max speed:     {telemetry.max_speed * 3.6:.1f} km/h")
        print(f"Start coords:  {telemetry.start_coordinates[0]:.6f}, {telemetry.start_coordinates[1]:.6f}")
        print(f"End coords:    {telemetry.end_coordinates[0]:.6f}, {telemetry.end_coordinates[1]:.6f}")

    elif path.suffix.upper() in ['.MP4', '.MOV', '.AVI', '.MKV']:
        print(f"Video File: {path}")
        print("-" * 50)
        info = get_video_info(path)
        print(f"Resolution:    {info['width']}x{info['height']}")
        print(f"FPS:           {info['fps']:.2f}")
        print(f"Frames:        {info['frame_count']}")
        print(f"Duration:      {info['duration_seconds']:.1f}s")

    else:
        print(f"Unknown file type: {path.suffix}")
        return 1

    return 0


def main():
    parser = argparse.ArgumentParser(
        description='DJI Telemetry Overlay - Overlay telemetry data on drone footage',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Process video with telemetry overlay (auto-detect SRT)
  %(prog)s overlay video.MP4 --audio

  # Generate transparent overlay video
  %(prog)s overlay-only telemetry.SRT -o overlay.mp4 --width 3840 --height 2160

  # Export telemetry to different formats
  %(prog)s export telemetry.SRT -o data.csv
  %(prog)s export telemetry.SRT -o data.json
  %(prog)s export telemetry.SRT -o flight.gpx

  # Show file information
  %(prog)s info video.SRT
'''
    )
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # === overlay command ===
    p_overlay = subparsers.add_parser('overlay', help='Process video with telemetry overlay')
    p_overlay.add_argument('video', help='Input video file (MP4)')
    p_overlay.add_argument('--srt', '-s', help='SRT telemetry file (default: same name as video)')
    p_overlay.add_argument('--output', '-o', help='Output video file')
    p_overlay.add_argument('--audio', '-a', action='store_true', help='Copy audio from original video')
    p_overlay.add_argument('--quiet', '-q', action='store_true', help='Suppress progress output')
    # Overlay options
    p_overlay.add_argument('--no-altitude', action='store_true', help='Hide altitude')
    p_overlay.add_argument('--no-speed', action='store_true', help='Hide horizontal speed')
    p_overlay.add_argument('--no-vspeed', action='store_true', help='Hide vertical speed')
    p_overlay.add_argument('--no-coords', action='store_true', help='Hide GPS coordinates')
    p_overlay.add_argument('--no-camera', action='store_true', help='Hide camera settings')
    p_overlay.add_argument('--no-timestamp', action='store_true', help='Hide timestamp')
    p_overlay.add_argument('--no-gauge', action='store_true', help='Hide speed gauge')
    p_overlay.add_argument('--gauge-max', type=float, default=50.0, help='Speed gauge max (km/h, default: 50)')
    p_overlay.set_defaults(func=cmd_overlay)

    # === overlay-only command ===
    p_overlay_only = subparsers.add_parser('overlay-only', help='Generate transparent overlay video')
    p_overlay_only.add_argument('srt', help='SRT telemetry file')
    p_overlay_only.add_argument('--output', '-o', help='Output video file')
    p_overlay_only.add_argument('--width', '-W', type=int, default=1920, help='Video width (default: 1920)')
    p_overlay_only.add_argument('--height', '-H', type=int, default=1080, help='Video height (default: 1080)')
    p_overlay_only.add_argument('--fps', type=float, default=30.0, help='Frames per second (default: 30)')
    p_overlay_only.add_argument('--quiet', '-q', action='store_true', help='Suppress progress output')
    # Overlay options
    p_overlay_only.add_argument('--no-altitude', action='store_true', help='Hide altitude')
    p_overlay_only.add_argument('--no-speed', action='store_true', help='Hide horizontal speed')
    p_overlay_only.add_argument('--no-vspeed', action='store_true', help='Hide vertical speed')
    p_overlay_only.add_argument('--no-coords', action='store_true', help='Hide GPS coordinates')
    p_overlay_only.add_argument('--no-camera', action='store_true', help='Hide camera settings')
    p_overlay_only.add_argument('--no-timestamp', action='store_true', help='Hide timestamp')
    p_overlay_only.add_argument('--no-gauge', action='store_true', help='Hide speed gauge')
    p_overlay_only.add_argument('--gauge-max', type=float, default=50.0, help='Speed gauge max (km/h)')
    p_overlay_only.set_defaults(func=cmd_overlay_only)

    # === frames command ===
    p_frames = subparsers.add_parser('frames', help='Generate transparent overlay frames (PNG sequence)')
    p_frames.add_argument('srt', help='SRT telemetry file')
    p_frames.add_argument('--output', '-o', help='Output directory')
    p_frames.add_argument('--width', '-W', type=int, default=1920, help='Frame width (default: 1920)')
    p_frames.add_argument('--height', '-H', type=int, default=1080, help='Frame height (default: 1080)')
    p_frames.add_argument('--fps', type=float, default=30.0, help='Frames per second (default: 30)')
    p_frames.add_argument('--format', '-f', default='png', choices=['png', 'jpg'], help='Image format')
    p_frames.add_argument('--quiet', '-q', action='store_true', help='Suppress progress output')
    # Overlay options
    p_frames.add_argument('--no-altitude', action='store_true', help='Hide altitude')
    p_frames.add_argument('--no-speed', action='store_true', help='Hide horizontal speed')
    p_frames.add_argument('--no-vspeed', action='store_true', help='Hide vertical speed')
    p_frames.add_argument('--no-coords', action='store_true', help='Hide GPS coordinates')
    p_frames.add_argument('--no-camera', action='store_true', help='Hide camera settings')
    p_frames.add_argument('--no-timestamp', action='store_true', help='Hide timestamp')
    p_frames.add_argument('--no-gauge', action='store_true', help='Hide speed gauge')
    p_frames.set_defaults(func=cmd_frames)

    # === export command ===
    p_export = subparsers.add_parser('export', help='Export telemetry to CSV, JSON, or GPX')
    p_export.add_argument('srt', help='SRT telemetry file')
    p_export.add_argument('--output', '-o', required=True, help='Output file (extension determines format)')
    p_export.add_argument('--format', '-f', choices=['csv', 'json', 'gpx'], help='Output format (auto-detected from extension)')
    p_export.set_defaults(func=cmd_export)

    # === info command ===
    p_info = subparsers.add_parser('info', help='Show information about video or SRT file')
    p_info.add_argument('path', help='Video or SRT file')
    p_info.set_defaults(func=cmd_info)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
