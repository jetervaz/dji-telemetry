"""
Video processing for telemetry overlay.
"""

import subprocess
from pathlib import Path
from typing import Callable, Optional

import cv2
import numpy as np

from .parser import TelemetryData
from .overlay import OverlayConfig, OverlayRenderer


def process_video(
    video_path: str | Path,
    telemetry: TelemetryData,
    output_path: str | Path,
    config: Optional[OverlayConfig] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Path:
    """
    Process a video file and add telemetry overlay.

    Args:
        video_path: Path to input video file
        telemetry: TelemetryData object with telemetry frames
        output_path: Path to output video file
        config: Overlay configuration (uses defaults if None)
        progress_callback: Optional callback function(current_frame, total_frames)

    Returns:
        Path to the output video file
    """
    video_path = Path(video_path)
    output_path = Path(output_path)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise IOError(f"Could not open video file: {video_path}")

    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Create overlay renderer
    renderer = OverlayRenderer(width, height, config)

    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    if not out.isOpened():
        cap.release()
        raise IOError(f"Could not create output video: {output_path}")

    frame_num = 0
    while True:
        ret, video_frame = cap.read()
        if not ret:
            break

        # Calculate current time in ms
        current_time_ms = (frame_num / fps) * 1000

        # Get telemetry for current time
        telem_frame = telemetry.get_frame_at_time(current_time_ms)

        if telem_frame:
            video_frame = renderer.render(telem_frame, video_frame)

        out.write(video_frame)
        frame_num += 1

        if progress_callback:
            progress_callback(frame_num, total_frames)

    cap.release()
    out.release()

    return output_path


def generate_overlay_video(
    telemetry: TelemetryData,
    output_path: str | Path,
    width: int = 1920,
    height: int = 1080,
    fps: float = 30.0,
    config: Optional[OverlayConfig] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Path:
    """
    Generate a transparent overlay video with just telemetry graphics.

    Args:
        telemetry: TelemetryData object with telemetry frames
        output_path: Path to output video file (recommended: .mov or .webm for transparency)
        width: Video width in pixels
        height: Video height in pixels
        fps: Frames per second
        config: Overlay configuration (uses defaults if None)
        progress_callback: Optional callback function(current_frame, total_frames)

    Returns:
        Path to the output video file

    Note:
        For transparency support, use:
        - .mov with PNG codec (best quality, large files)
        - .webm with VP9 codec (good compression, wide support)
    """
    output_path = Path(output_path)

    # Create overlay renderer
    renderer = OverlayRenderer(width, height, config)

    # Calculate total frames from telemetry duration
    duration_ms = telemetry.duration_seconds * 1000
    total_frames = int((duration_ms / 1000.0) * fps)

    # Determine output format based on extension
    ext = output_path.suffix.lower()

    if ext == '.mov':
        # Use PNG codec for MOV (supports alpha)
        fourcc = cv2.VideoWriter_fourcc(*'png ')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height), isColor=True)
        use_alpha = False  # OpenCV VideoWriter doesn't support alpha directly
    elif ext == '.webm':
        # VP9 codec
        fourcc = cv2.VideoWriter_fourcc(*'VP90')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        use_alpha = False
    else:
        # Default to mp4v
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        use_alpha = False

    if not out.isOpened():
        raise IOError(f"Could not create output video: {output_path}")

    for frame_num in range(total_frames):
        current_time_ms = (frame_num / fps) * 1000
        telem_frame = telemetry.get_frame_at_time(current_time_ms)

        if telem_frame:
            # Render on transparent background
            overlay = renderer.render(telem_frame, None)

            if use_alpha:
                out.write(overlay)
            else:
                # Convert BGRA to BGR with black background
                bgr_frame = cv2.cvtColor(overlay, cv2.COLOR_BGRA2BGR)
                out.write(bgr_frame)
        else:
            # Write black frame
            black_frame = np.zeros((height, width, 3), dtype=np.uint8)
            out.write(black_frame)

        if progress_callback:
            progress_callback(frame_num + 1, total_frames)

    out.release()

    return output_path


def generate_overlay_frames(
    telemetry: TelemetryData,
    output_dir: str | Path,
    width: int = 1920,
    height: int = 1080,
    fps: float = 30.0,
    config: Optional[OverlayConfig] = None,
    format: str = 'png',
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Path:
    """
    Generate transparent overlay frames as individual images.

    This is useful for compositing in video editors that support image sequences
    with alpha channels.

    Args:
        telemetry: TelemetryData object with telemetry frames
        output_dir: Directory to save frame images
        width: Frame width in pixels
        height: Frame height in pixels
        fps: Frames per second (determines number of frames)
        config: Overlay configuration (uses defaults if None)
        format: Image format ('png' recommended for transparency)
        progress_callback: Optional callback function(current_frame, total_frames)

    Returns:
        Path to the output directory
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    renderer = OverlayRenderer(width, height, config)

    duration_ms = telemetry.duration_seconds * 1000
    total_frames = int((duration_ms / 1000.0) * fps)

    for frame_num in range(total_frames):
        current_time_ms = (frame_num / fps) * 1000
        telem_frame = telemetry.get_frame_at_time(current_time_ms)

        if telem_frame:
            overlay = renderer.render(telem_frame, None)
        else:
            overlay = np.zeros((height, width, 4), dtype=np.uint8)

        frame_path = output_dir / f"frame_{frame_num:06d}.{format}"
        cv2.imwrite(str(frame_path), overlay)

        if progress_callback:
            progress_callback(frame_num + 1, total_frames)

    return output_dir


def add_audio(
    video_path: str | Path,
    audio_source: str | Path,
    output_path: str | Path,
    ffmpeg_path: str = 'ffmpeg'
) -> Path:
    """
    Add audio from source file to video using ffmpeg.

    Args:
        video_path: Path to video file (without audio)
        audio_source: Path to file containing audio track
        output_path: Path to output video file
        ffmpeg_path: Path to ffmpeg executable

    Returns:
        Path to the output video file
    """
    video_path = Path(video_path)
    audio_source = Path(audio_source)
    output_path = Path(output_path)

    cmd = [
        ffmpeg_path, '-y',
        '-i', str(video_path),
        '-i', str(audio_source),
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-map', '0:v:0',
        '-map', '1:a:0?',  # ? makes audio optional
        '-shortest',
        str(output_path)
    ]

    try:
        subprocess.run(cmd, capture_output=True, check=True)
    except subprocess.CalledProcessError:
        # If no audio, just copy the video
        import shutil
        shutil.copy(video_path, output_path)

    return output_path


def get_video_info(video_path: str | Path) -> dict:
    """
    Get video file information.

    Args:
        video_path: Path to video file

    Returns:
        Dictionary with video properties
    """
    video_path = Path(video_path)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise IOError(f"Could not open video file: {video_path}")

    info = {
        'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        'fps': cap.get(cv2.CAP_PROP_FPS),
        'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        'duration_seconds': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / cap.get(cv2.CAP_PROP_FPS),
        'fourcc': int(cap.get(cv2.CAP_PROP_FOURCC)),
    }

    cap.release()
    return info
