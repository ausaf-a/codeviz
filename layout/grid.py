"""Grid-based layout algorithm for room placement."""

from dataclasses import dataclass
from typing import Iterator
import math


@dataclass
class RoomLayout:
    """Layout information for a single room."""
    file_path: str
    relative_path: str
    directory: str
    filename: str
    position: tuple[float, float, float]  # x, y, z
    dimensions: tuple[float, float, float]  # width, depth, height
    rotation: float  # y-axis rotation in radians


@dataclass
class LayoutConfig:
    """Configuration for layout generation."""
    room_width: float = 6.0       # Room width (x-axis)
    room_height: float = 4.0      # Room height (y-axis)
    min_room_depth: float = 4.0   # Minimum room depth (z-axis)
    max_room_depth: float = 12.0  # Maximum room depth (z-axis)
    room_spacing: float = 2.0     # Gap between rooms
    dir_spacing: float = 8.0      # Gap between directory clusters
    max_rooms_per_row: int = 5    # Max rooms in a row within a directory


def compute_layout(
    files: list[dict],
    config: LayoutConfig | None = None,
) -> list[RoomLayout]:
    """
    Compute 3D layout for a list of files.

    Args:
        files: List of file dicts from parser (must have directory, loc, etc.)
        config: Layout configuration

    Returns:
        List of RoomLayout objects with positions
    """
    config = config or LayoutConfig()

    # Group files by directory
    dir_files: dict[str, list[dict]] = {}
    for f in files:
        d = f.get("directory", "")
        if d not in dir_files:
            dir_files[d] = []
        dir_files[d].append(f)

    # Sort directories for consistent ordering
    sorted_dirs = sorted(dir_files.keys())

    layouts = []

    # Position each directory cluster
    dir_x_offset = 0.0

    for dir_name in sorted_dirs:
        dir_file_list = dir_files[dir_name]

        # Calculate grid for this directory
        num_files = len(dir_file_list)
        cols = min(num_files, config.max_rooms_per_row)
        rows = math.ceil(num_files / cols)

        # Position each file in the directory
        for idx, file_info in enumerate(dir_file_list):
            row = idx // cols
            col = idx % cols

            # Calculate room depth based on LOC
            loc = file_info.get("loc", 50)
            depth_factor = min(loc / 100, 1.0)  # Normalize to 0-1
            room_depth = (
                config.min_room_depth +
                (config.max_room_depth - config.min_room_depth) * depth_factor
            )

            # Calculate position
            x = dir_x_offset + col * (config.room_width + config.room_spacing)
            y = 0  # Ground level
            z = row * (config.max_room_depth + config.room_spacing)

            layouts.append(RoomLayout(
                file_path=file_info["path"],
                relative_path=file_info["relative_path"],
                directory=dir_name,
                filename=file_info["filename"],
                position=(x, y, z),
                dimensions=(config.room_width, room_depth, config.room_height),
                rotation=0.0,
            ))

        # Move x offset for next directory
        cluster_width = cols * (config.room_width + config.room_spacing)
        dir_x_offset += cluster_width + config.dir_spacing

    return layouts


def get_layout_bounds(layouts: list[RoomLayout]) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """
    Calculate bounding box of all rooms.

    Returns:
        Tuple of (min_corner, max_corner) as (x, y, z) tuples
    """
    if not layouts:
        return ((0, 0, 0), (0, 0, 0))

    min_x = min(r.position[0] for r in layouts)
    min_y = min(r.position[1] for r in layouts)
    min_z = min(r.position[2] for r in layouts)

    max_x = max(r.position[0] + r.dimensions[0] for r in layouts)
    max_y = max(r.position[1] + r.dimensions[2] for r in layouts)  # height is dim[2]
    max_z = max(r.position[2] + r.dimensions[1] for r in layouts)  # depth is dim[1]

    return ((min_x, min_y, min_z), (max_x, max_y, max_z))


def get_spawn_point(layouts: list[RoomLayout]) -> tuple[float, float, float]:
    """
    Calculate a good spawn point for VR viewer.

    Returns:
        (x, y, z) position for player spawn
    """
    bounds_min, bounds_max = get_layout_bounds(layouts)

    # Spawn in front of the first row, centered
    x = (bounds_min[0] + bounds_max[0]) / 2
    y = 1.6  # Eye height
    z = bounds_min[2] - 5.0  # In front of first row

    return (x, y, z)
