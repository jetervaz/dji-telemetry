"""
Export telemetry data to various formats (CSV, JSON, GPX).
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET
from xml.dom import minidom

from .parser import TelemetryData


def to_csv(data: TelemetryData, output_path: str | Path, include_all_fields: bool = True) -> Path:
    """
    Export telemetry data to CSV format.

    Args:
        data: TelemetryData object
        output_path: Output file path
        include_all_fields: Include all fields or just essential ones

    Returns:
        Path to the created file
    """
    output_path = Path(output_path)

    if include_all_fields:
        fieldnames = [
            'frame_num', 'timestamp', 'start_time_ms', 'end_time_ms',
            'latitude', 'longitude', 'rel_altitude_m', 'abs_altitude_m',
            'h_speed_ms', 'h_speed_kmh', 'v_speed_ms', 'distance_m',
            'iso', 'shutter', 'fnum', 'ev', 'color_temp'
        ]
    else:
        fieldnames = [
            'timestamp', 'latitude', 'longitude', 'rel_altitude_m',
            'h_speed_kmh', 'v_speed_ms'
        ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for frame in data.frames:
            writer.writerow(frame.to_dict())

    return output_path


def to_json(data: TelemetryData, output_path: str | Path, indent: int = 2) -> Path:
    """
    Export telemetry data to JSON format.

    Args:
        data: TelemetryData object
        output_path: Output file path
        indent: JSON indentation level (None for compact)

    Returns:
        Path to the created file
    """
    output_path = Path(output_path)

    output = {
        'metadata': {
            'source_file': data.source_file,
            'total_frames': len(data.frames),
            'duration_seconds': data.duration_seconds,
            'total_distance_m': data.total_distance,
            'max_altitude_m': data.max_altitude,
            'max_speed_kmh': data.max_speed * 3.6,
            'start_coordinates': {
                'latitude': data.start_coordinates[0],
                'longitude': data.start_coordinates[1]
            },
            'end_coordinates': {
                'latitude': data.end_coordinates[0],
                'longitude': data.end_coordinates[1]
            }
        },
        'frames': data.to_list()
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=indent)

    return output_path


def to_gpx(
    data: TelemetryData,
    output_path: str | Path,
    name: Optional[str] = None,
    description: Optional[str] = None
) -> Path:
    """
    Export telemetry data to GPX format.

    Args:
        data: TelemetryData object
        output_path: Output file path
        name: Track name (defaults to source filename)
        description: Track description

    Returns:
        Path to the created file
    """
    output_path = Path(output_path)

    # Create GPX root element
    gpx = ET.Element('gpx')
    gpx.set('version', '1.1')
    gpx.set('creator', 'dji-telemetry-overlay')
    gpx.set('xmlns', 'http://www.topografix.com/GPX/1/1')
    gpx.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    gpx.set('xsi:schemaLocation', 'http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd')

    # Metadata
    metadata = ET.SubElement(gpx, 'metadata')
    if name or data.source_file:
        name_elem = ET.SubElement(metadata, 'name')
        name_elem.text = name or Path(data.source_file).stem if data.source_file else 'DJI Flight'
    if description:
        desc_elem = ET.SubElement(metadata, 'desc')
        desc_elem.text = description

    # Create track
    trk = ET.SubElement(gpx, 'trk')

    trk_name = ET.SubElement(trk, 'name')
    trk_name.text = name or (Path(data.source_file).stem if data.source_file else 'DJI Flight')

    # Track segment
    trkseg = ET.SubElement(trk, 'trkseg')

    # Add track points
    for frame in data.frames:
        trkpt = ET.SubElement(trkseg, 'trkpt')
        trkpt.set('lat', f'{frame.latitude:.6f}')
        trkpt.set('lon', f'{frame.longitude:.6f}')

        # Elevation (using absolute altitude for GPX)
        ele = ET.SubElement(trkpt, 'ele')
        ele.text = f'{frame.abs_alt:.1f}'

        # Time
        if frame.timestamp:
            time_elem = ET.SubElement(trkpt, 'time')
            try:
                # Parse timestamp and convert to ISO format
                dt = datetime.strptime(frame.timestamp, '%Y-%m-%d %H:%M:%S.%f')
                time_elem.text = dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            except ValueError:
                pass

        # Extensions for speed data
        extensions = ET.SubElement(trkpt, 'extensions')

        speed = ET.SubElement(extensions, 'speed')
        speed.text = f'{frame.h_speed:.2f}'

        vspeed = ET.SubElement(extensions, 'vspeed')
        vspeed.text = f'{frame.v_speed:.2f}'

    # Pretty print
    xml_str = ET.tostring(gpx, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent='  ')

    # Remove extra blank lines
    lines = [line for line in pretty_xml.split('\n') if line.strip()]
    pretty_xml = '\n'.join(lines)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)

    return output_path


def export(
    data: TelemetryData,
    output_path: str | Path,
    format: Optional[str] = None
) -> Path:
    """
    Export telemetry data to specified format (auto-detected from extension if not specified).

    Args:
        data: TelemetryData object
        output_path: Output file path
        format: Output format ('csv', 'json', 'gpx') - auto-detected if None

    Returns:
        Path to the created file
    """
    output_path = Path(output_path)

    if format is None:
        format = output_path.suffix.lower().lstrip('.')

    if format == 'csv':
        return to_csv(data, output_path)
    elif format == 'json':
        return to_json(data, output_path)
    elif format == 'gpx':
        return to_gpx(data, output_path)
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'csv', 'json', or 'gpx'.")
