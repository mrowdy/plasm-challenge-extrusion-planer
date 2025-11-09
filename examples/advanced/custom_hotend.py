"""Custom hotend and material configuration example.

This example demonstrates:
- Using different hotend profiles (Standard, Fast Response, Induction)
- Testing with different materials (PLA, PETG, TPU variants)
- Comparing how equipment and material choices affect compensation
- Understanding the combined effect of hotend speed and material softness

Shows how to adapt the planner to your specific 3D printer setup.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from plot_helper import save_comparison_plot

from extrusion_planner import ExtrusionPlanner, Segment
from extrusion_planner.profiles import (
    HotendProfile,
    MaterialType,
    create_hotend_config,
    create_material_config,
)


def create_challenging_segments():
    """Create a challenging sequence that triggers compensation.

    This represents a perimeter-to-infill transition:
    - Slow perimeter printing (precise, low flow)
    - Fast infill printing (high flow - may exceed hotend limit)
    - Back to perimeter (pressure compensation important here)

    Returns:
        List of segments
    """
    return [
        # Outer perimeter (slow, precise)
        Segment(length=15.0, feed_rate=60.0, extrusion=0.3),
        Segment(length=15.0, feed_rate=60.0, extrusion=0.3),
        # Fast infill (high flow - exceeds standard hotend limit)
        # Flow = (52.0 / 10.0) * (180.0 / 60) = 5.2 * 3.0 = 15.6 mm³/s
        Segment(length=10.0, feed_rate=180.0, extrusion=52.0),
        Segment(length=10.0, feed_rate=180.0, extrusion=52.0),
        # Back to perimeter
        Segment(length=15.0, feed_rate=60.0, extrusion=0.3),
        Segment(length=15.0, feed_rate=60.0, extrusion=0.3),
    ]


def analyze_combination(planner, segments, hotend_profile, material_type, save_plot=False):
    """Analyze a specific hotend/material combination.

    Args:
        planner: ExtrusionPlanner instance
        segments: List of segments to process
        hotend_profile: HotendProfile enum value
        material_type: MaterialType enum value
        save_plot: If True, generate and save a comparison plot
    """
    hotend = create_hotend_config(hotend_profile)
    material = create_material_config(material_type)

    adjusted = planner.process(segments, hotend, material)

    adjustments = sum(
        1 for orig, adj in zip(segments, adjusted) if abs(orig.feed_rate - adj.feed_rate) > 0.1
    )

    max_reduction = 0.0
    for orig, adj in zip(segments, adjusted):
        if orig.feed_rate > 0:
            reduction = (1 - adj.feed_rate / orig.feed_rate) * 100
            max_reduction = max(max_reduction, reduction)

    # Calculate average feed rate change
    avg_feed_orig = sum(s.feed_rate for s in segments) / len(segments)
    avg_feed_adj = sum(s.feed_rate for s in adjusted) / len(adjusted)
    avg_change = (1 - avg_feed_adj / avg_feed_orig) * 100

    # Display results
    print(f"\n{hotend_profile.value.replace('_', ' ').title()} + {material.name}")
    print("  " + "-" * 70)
    print(
        f"  Hotend: {hotend.max_volumetric_flow} mm³/s max, "
        f"{hotend.response_time * 1000:.0f}ms response"
    )
    print(f"  Material: Shore {material.shore_hardness}")
    print(f"  Segments adjusted: {adjustments}/{len(segments)}")
    print(f"  Max feed reduction: {max_reduction:.1f}%")
    print(f"  Avg feed change: {avg_change:.1f}%")

    # Show segment-by-segment details
    print(f"\n  {'Seg':<4} {'Original':<12} {'Adjusted':<12} {'Change'}")
    print(f"  {'#':<4} {'(mm/min)':<12} {'(mm/min)':<12} {'(%)'}")
    for i, (orig, adj) in enumerate(zip(segments, adjusted)):
        change = (1 - adj.feed_rate / orig.feed_rate) * 100 if orig.feed_rate > 0 else 0.0
        marker = " *" if abs(change) > 0.1 else ""
        print(f"  {i:<4} {orig.feed_rate:<12.1f} {adj.feed_rate:<12.1f} {change:>6.1f}{marker}")

    if save_plot:
        import os

        plot_name = f"{hotend_profile.value}_{material_type.value}"
        script_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(script_dir, f"custom_hotend_{plot_name}.png")
        title = f"{hotend_profile.value.replace('_', ' ').title()} + {material.name}"
        save_comparison_plot(segments, adjusted, hotend, material, filename, title)


def main():
    """Compare different hotend and material combinations."""

    print("=" * 80)
    print("CUSTOM HOTEND & MATERIAL CONFIGURATION")
    print("=" * 80)
    print("\nThis example shows how different equipment and materials affect compensation.\n")

    # Create test segments
    segments = create_challenging_segments()

    # Create planner
    planner = ExtrusionPlanner(lookahead_window=4)

    print(f"Test scenario: {len(segments)} segments")
    print("  - Slow perimeter (60 mm/min)")
    print("  - Fast infill (180 mm/min)")
    print("  - Back to perimeter")

    print("\n" + "=" * 80)
    print("SCENARIO 1: WORST CASE (Maximum Compensation)")
    print("=" * 80)
    analyze_combination(
        planner, segments, HotendProfile.STANDARD, MaterialType.TPU_SHORE_30, save_plot=True
    )

    print("\n" + "=" * 80)
    print("SCENARIO 2: BEST CASE (Minimal Compensation)")
    print("=" * 80)
    analyze_combination(
        planner, segments, HotendProfile.INDUCTION, MaterialType.PLA, save_plot=True
    )

    print("\n" + "=" * 80)
    print("SCENARIO 3: MID-RANGE (Moderate Compensation)")
    print("=" * 80)
    analyze_combination(
        planner, segments, HotendProfile.STANDARD, MaterialType.PETG, save_plot=True
    )

    print("\n" + "=" * 80)
    print("SCENARIO 4: FAST HOTEND + SOFT MATERIAL")
    print("=" * 80)
    analyze_combination(
        planner, segments, HotendProfile.INDUCTION, MaterialType.TPU_SHORE_30, save_plot=True
    )


if __name__ == "__main__":
    main()
