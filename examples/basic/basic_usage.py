"""Basic usage example.

This example demonstrates:
- Creating segments
- Setting up hotend and material configurations
- Processing segments through the planner
- Displaying before/after results

This is the simplest way to use the extrusion planner.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from plot_helper import generate_example_plot

from extrusion_planner import ExtrusionPlanner, HotendConfig, MaterialConfig, Segment


def main():
    """Basic usage example with given values."""

    print("=" * 80)
    print("BASIC EXTRUSION PLANNER USAGE")
    print("=" * 80)

    # Realistic perimeter-to-infill transition (8 segments)
    # This demonstrates: slow perimeter → fast infill → back to perimeter
    segments = [
        # Slow perimeter printing (low flow)
        Segment(length=15.0, feed_rate=60.0, extrusion=0.3),
        Segment(length=15.0, feed_rate=60.0, extrusion=0.3),
        # Transition to fast infill (flow will exceed hotend limit!)
        Segment(length=10.0, feed_rate=180.0, extrusion=50.0),
        Segment(length=10.0, feed_rate=180.0, extrusion=50.0),
        Segment(length=10.0, feed_rate=180.0, extrusion=50.0),
        # Back to slow perimeter (pressure compensation will activate here)
        Segment(length=15.0, feed_rate=60.0, extrusion=0.3),
        Segment(length=15.0, feed_rate=60.0, extrusion=0.3),
        Segment(length=15.0, feed_rate=60.0, extrusion=0.3),
    ]

    # Hotend configuration (equipment properties)
    # max_volumetric_flow: Maximum plastic melting rate (mm³/s)
    # response_time: How fast the hotend responds to changes (seconds)
    hotend = HotendConfig(
        max_volumetric_flow=12.0,  # mm³/s
        response_time=0.05,  # seconds (50ms - typical standard hotend)
    )

    # Material configuration (material properties)
    # shore_hardness: Shore A hardness scale (0-100)
    #   - 100 = rigid (like hard PLA)
    #   - 30 = very soft (like flexible TPU)
    material = MaterialConfig(
        name="TPU Shore 30",
        shore_hardness=30,  # Very soft material
    )

    print("\nInput Configuration:")
    print(
        f"  Hotend: {hotend.max_volumetric_flow} mm³/s max flow, "
        f"{hotend.response_time * 1000:.0f}ms response"
    )
    print(f"  Material: {material.name} (Shore {material.shore_hardness})")
    print(f"  Segments: {len(segments)} moves to process\n")

    # Display original segments
    print("Original Segments:")
    print(f"  {'#':<4} {'Length':<10} {'Feed Rate':<12} {'Extrusion':<12} {'Flow Rate'}")
    print(f"  {'':4} {'(mm)':<10} {'(mm/min)':<12} {'(mm³)':<12} {'(mm³/s)'}")
    print("  " + "-" * 70)

    for i, seg in enumerate(segments):
        flow = seg.extrusion_rate()
        print(
            f"  {i:<4} {seg.length:<10.1f} {seg.feed_rate:<12.1f} "
            f"{seg.extrusion:<12.2f} {flow:<.2f}"
        )

    # Create planner with 5-segment look-ahead window (default)
    planner = ExtrusionPlanner(lookahead_window=5)

    # Process segments
    print("\nProcessing segments...")
    adjusted_segments = planner.process(segments, hotend, material)
    print("Done!\n")

    # Display adjusted segments
    print("Adjusted Segments:")
    print(f"  {'#':<4} {'Length':<10} {'Feed Rate':<12} {'Extrusion':<12} {'Flow Rate'}")
    print(f"  {'':4} {'(mm)':<10} {'(mm/min)':<12} {'(mm³)':<12} {'(mm³/s)'}")
    print("  " + "-" * 70)

    for i, seg in enumerate(adjusted_segments):
        flow = seg.extrusion_rate()
        print(
            f"  {i:<4} {seg.length:<10.1f} {seg.feed_rate:<12.1f} "
            f"{seg.extrusion:<12.2f} {flow:<.2f}"
        )

    # Show adjustments made
    print("\nAdjustments Summary:")
    print("  " + "-" * 70)
    adjustments_made = False

    for i, (orig, adj) in enumerate(zip(segments, adjusted_segments)):
        if abs(orig.feed_rate - adj.feed_rate) > 0.1:
            reduction_pct = (1 - adj.feed_rate / orig.feed_rate) * 100
            print(
                f"  Segment {i}: {orig.feed_rate:.1f} -> {adj.feed_rate:.1f} mm/min "
                f"({reduction_pct:.1f}% reduction)"
            )
            adjustments_made = True

    if not adjustments_made:
        print("  No adjustments needed - all segments within safe limits!")

    adjusted_count = sum(
        1 for o, a in zip(segments, adjusted_segments) if abs(o.feed_rate - a.feed_rate) > 0.1
    )
    print(f"\nTotal segments adjusted: {adjusted_count}/{len(segments)}")

    print("\n" + "=" * 80)
    print("GENERATING PLOT")
    print("=" * 80)
    generate_example_plot("basic_usage", segments, adjusted_segments, hotend, material)
    print()


if __name__ == "__main__":
    main()
