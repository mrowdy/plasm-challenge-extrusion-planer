"""Helper functions for creating matplotlib plots in examples."""

import os
from typing import List, Optional

from extrusion_planner import HotendConfig, MaterialConfig, Segment
from extrusion_planner.visualize import plot_comparison


def save_comparison_plot(
    original_segments: List[Segment],
    adjusted_segments: List[Segment],
    hotend: HotendConfig,
    material: MaterialConfig,
    filename: str,
    title: Optional[str] = None,
) -> None:
    """Save a comparison plot to file.

    Args:
        original_segments: Original segments before adjustment
        adjusted_segments: Adjusted segments after planner
        hotend: Hotend configuration
        material: Material configuration
        filename: Output filename (e.g., "my_plot.png")
        title: Optional custom title
    """
    if not filename.endswith((".png", ".jpg", ".pdf")):
        filename += ".png"

    plot_comparison(
        original_segments=original_segments,
        adjusted_segments=adjusted_segments,
        hotend=hotend,
        material=material,
        title=title,
        show=False,
        save_path=filename,
    )
    print(f"  Plot saved: {filename}")


def generate_example_plot(
    name: str,
    original_segments: List[Segment],
    adjusted_segments: List[Segment],
    hotend: HotendConfig,
    material: MaterialConfig,
    output_dir: Optional[str] = None,
) -> None:
    """Generate and save a plot with automatic naming.

    Args:
        name: Base name for the plot (e.g., "basic_usage")
        original_segments: Original segments
        adjusted_segments: Adjusted segments
        hotend: Hotend configuration
        material: Material configuration
        output_dir: Optional output directory (defaults to caller's directory)
    """
    if output_dir is None:
        import inspect

        caller_frame = inspect.stack()[1]
        caller_file = caller_frame.filename
        output_dir = os.path.dirname(os.path.abspath(caller_file))

    filename = os.path.join(output_dir, f"{name}_plot.png")
    title = f"{name.replace('_', ' ').title()}: {material.name}"

    save_comparison_plot(
        original_segments=original_segments,
        adjusted_segments=adjusted_segments,
        hotend=hotend,
        material=material,
        filename=filename,
        title=title,
    )
