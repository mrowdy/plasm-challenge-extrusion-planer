"""Visualization utilities for extrusion planning analysis.

This module provides functions to visualize feed rate adjustments, volumetric flow
rates, and pressure compensation effects.
"""

from typing import List, Optional

import matplotlib.pyplot as plt
import numpy as np

from extrusion_planner.models import HotendConfig, MaterialConfig, Segment
from extrusion_planner.pressure import DecayModel, PressureModel


def _calculate_cumulative_time(segments: List[Segment]) -> np.ndarray:
    """Calculate cumulative time for each segment.

    Args:
        segments: List of segments

    Returns:
        Array of cumulative times at the start of each segment
    """
    times = [0.0]
    for seg in segments[:-1]:
        times.append(times[-1] + seg.travel_time())
    return np.array(times)


def plot_comparison(
    original_segments: List[Segment],
    adjusted_segments: List[Segment],
    hotend: HotendConfig,
    material: MaterialConfig,
    title: Optional[str] = None,
    show: bool = True,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """Plot before/after comparison of extrusion planning adjustments.

    Creates a multi-panel visualization showing:
    - Feed rate over time (original vs adjusted)
    - Volumetric flow over time with hotend limit line
    - Pressure model state over time

    Args:
        original_segments: Original unadjusted segments
        adjusted_segments: Adjusted segments from planner
        hotend: Hotend configuration
        material: Material configuration
        title: Optional custom title (default: auto-generated)
        show: Whether to display the plot (default: True)
        save_path: Optional path to save the figure

    Returns:
        matplotlib Figure object

    Example:
        >>> from extrusion_planner import ExtrusionPlanner
        >>> planner = ExtrusionPlanner()
        >>> adjusted = planner.process(segments, hotend, material)
        >>> plot_comparison(segments, adjusted, hotend, material)
    """
    if len(original_segments) != len(adjusted_segments):
        raise ValueError(
            f"Segment lists must be same length: "
            f"{len(original_segments)} != {len(adjusted_segments)}"
        )

    if not original_segments:
        raise ValueError("Cannot plot empty segment list")

    # Calculate time arrays
    times_orig = _calculate_cumulative_time(original_segments)
    times_adj = _calculate_cumulative_time(adjusted_segments)

    # Extract feed rates and flows
    feed_rates_orig = np.array([seg.feed_rate for seg in original_segments])
    feed_rates_adj = np.array([seg.feed_rate for seg in adjusted_segments])
    flows_orig = np.array([seg.extrusion_rate() for seg in original_segments])
    flows_adj = np.array([seg.extrusion_rate() for seg in adjusted_segments])

    # Simulate pressure model for adjusted segments
    pressure_model = PressureModel(
        hotend=hotend, material=material, decay_model=DecayModel.EXPONENTIAL
    )
    pressure_levels = []
    for seg in adjusted_segments:
        pressure_model.update(seg.extrusion_rate(), seg.travel_time())
        pressure_levels.append(pressure_model.current_level)
    pressure_levels = np.array(pressure_levels)

    # Create figure with 3 subplots
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

    # Auto-generate title if not provided
    if title is None:
        title = (
            f"Extrusion Planning Analysis\n"
            f"Hotend: {hotend.max_volumetric_flow:.1f} mm³/s, "
            f"Response: {hotend.response_time*1000:.0f}ms | "
            f"Material: {material.name} (Shore {material.shore_hardness})"
        )

    fig.suptitle(title, fontsize=14, fontweight="bold")

    # Plot 1: Feed Rate
    ax1.step(times_orig, feed_rates_orig, where="post", label="Original", alpha=0.7)
    ax1.step(times_adj, feed_rates_adj, where="post", label="Adjusted", linewidth=2)
    ax1.set_ylabel("Feed Rate (mm/min)")
    ax1.set_title("Feed Rate Adjustments")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Plot 2: Volumetric Flow
    ax2.step(times_orig, flows_orig, where="post", label="Original", alpha=0.7)
    ax2.step(times_adj, flows_adj, where="post", label="Adjusted", linewidth=2)
    ax2.axhline(
        hotend.max_volumetric_flow,
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Hotend Limit ({hotend.max_volumetric_flow:.1f} mm³/s)",
    )
    ax2.set_ylabel("Volumetric Flow (mm³/s)")
    ax2.set_title("Volumetric Flow vs Hotend Capacity")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Plot 3: Pressure Level
    ax3.step(
        times_adj,
        pressure_levels,
        where="post",
        color="purple",
        linewidth=2,
        label="Pressure Level",
    )
    ax3.axhline(
        0.8, color="orange", linestyle="--", alpha=0.7, label="High Pressure Threshold (0.8)"
    )
    ax3.set_ylabel("Pressure Level (0-1)")
    ax3.set_xlabel("Time (seconds)")
    ax3.set_title("Hotend Pressure State (Adjusted Segments)")
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    ax3.set_ylim(-0.05, 1.05)

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    if show:
        plt.show()

    return fig


def plot_feed_rate_only(
    original_segments: List[Segment],
    adjusted_segments: List[Segment],
    title: str = "Feed Rate Comparison",
    show: bool = True,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """Plot simple feed rate comparison (single panel).

    Args:
        original_segments: Original unadjusted segments
        adjusted_segments: Adjusted segments from planner
        title: Plot title
        show: Whether to display the plot
        save_path: Optional path to save the figure

    Returns:
        matplotlib Figure object
    """
    if len(original_segments) != len(adjusted_segments):
        raise ValueError("Segment lists must be same length")

    if not original_segments:
        raise ValueError("Cannot plot empty segment list")

    times_orig = _calculate_cumulative_time(original_segments)
    times_adj = _calculate_cumulative_time(adjusted_segments)
    feed_rates_orig = np.array([seg.feed_rate for seg in original_segments])
    feed_rates_adj = np.array([seg.feed_rate for seg in adjusted_segments])

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.step(times_orig, feed_rates_orig, where="post", label="Original", alpha=0.7)
    ax.step(times_adj, feed_rates_adj, where="post", label="Adjusted", linewidth=2)
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Feed Rate (mm/min)")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    if show:
        plt.show()

    return fig


def plot_flow_only(
    segments: List[Segment],
    hotend: HotendConfig,
    title: str = "Volumetric Flow Analysis",
    show: bool = True,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """Plot volumetric flow with hotend limit (single panel).

    Args:
        segments: Segments to analyze
        hotend: Hotend configuration
        title: Plot title
        show: Whether to display the plot
        save_path: Optional path to save the figure

    Returns:
        matplotlib Figure object
    """
    if not segments:
        raise ValueError("Cannot plot empty segment list")

    times = _calculate_cumulative_time(segments)
    flows = np.array([seg.extrusion_rate() for seg in segments])

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.step(times, flows, where="post", linewidth=2, label="Volumetric Flow")
    ax.axhline(
        hotend.max_volumetric_flow,
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Hotend Limit ({hotend.max_volumetric_flow:.1f} mm³/s)",
    )
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Volumetric Flow (mm³/s)")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    if show:
        plt.show()

    return fig
