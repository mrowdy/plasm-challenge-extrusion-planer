"""Visualize flow analysis for a sequence of segments.

This demonstrates the current implementation (Phases 1-4) by showing:
- Volumetric flow rates over time
- Hotend capacity limits
- High-flow regions that need adjustment
- Look-ahead predictions at different points
"""

import matplotlib.pyplot as plt

from extrusion_planner.flow_calculator import calculate_volumetric_flow, check_flow_limit
from extrusion_planner.lookahead import (
    HIGH_FLOW_THRESHOLD_RATIO,
    LookAheadBuffer,
    predict_flow_window,
)
from extrusion_planner.models.hotend import HotendConfig
from extrusion_planner.models.material import MaterialConfig
from extrusion_planner.models.segment import Segment


def create_test_segments():
    """Create a realistic test sequence with flow challenges."""
    # Scenario: Slow perimeter -> Fast infill -> Slow perimeter -> Fast infill
    segments = [
        # Slow outer perimeter (low flow)
        Segment(length=20.0, feed_rate=40.0, extrusion=26.0),  # 1.3 mm³/s
        Segment(length=20.0, feed_rate=40.0, extrusion=26.0),
        Segment(length=20.0, feed_rate=40.0, extrusion=26.0),
        # Fast infill (high flow - will exceed limit!)
        Segment(length=30.0, feed_rate=120.0, extrusion=210.0),  # 14 mm³/s
        Segment(length=30.0, feed_rate=120.0, extrusion=210.0),
        Segment(length=30.0, feed_rate=120.0, extrusion=210.0),
        Segment(length=30.0, feed_rate=120.0, extrusion=210.0),
        # Travel move
        Segment(length=50.0, feed_rate=300.0, extrusion=0.0),  # 0 mm³/s
        # Back to slow perimeter
        Segment(length=20.0, feed_rate=40.0, extrusion=26.0),  # 1.3 mm³/s
        Segment(length=20.0, feed_rate=40.0, extrusion=26.0),
        # Another fast infill burst
        Segment(length=30.0, feed_rate=120.0, extrusion=210.0),  # 14 mm³/s
        Segment(length=30.0, feed_rate=120.0, extrusion=210.0),
        Segment(length=30.0, feed_rate=120.0, extrusion=210.0),
        # Final perimeter
        Segment(length=20.0, feed_rate=40.0, extrusion=26.0),  # 1.3 mm³/s
    ]
    return segments


def analyze_segments(segments, hotend):
    """Analyze segments and extract time-series data."""
    times = []
    flows = []
    feed_rates = []
    violations = []

    current_time = 0.0

    for seg in segments:
        # Record data at start of segment
        times.append(current_time)
        flow = calculate_volumetric_flow(seg)
        flows.append(flow)
        feed_rates.append(seg.feed_rate)
        violations.append(check_flow_limit(seg, hotend))

        # Advance time
        current_time += seg.travel_time()

    # Add final time point for step plot
    times.append(current_time)

    return times, flows, feed_rates, violations


def plot_flow_analysis(segments, hotend, material):
    """Create comprehensive flow analysis visualization."""
    times, flows, feed_rates, violations = analyze_segments(segments, hotend)

    # Create figure with 3 subplots
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    fig.suptitle(
        f"Flow Analysis: {material.name} on {hotend.max_volumetric_flow} mm³/s Hotend",
        fontsize=14,
        fontweight="bold",
    )

    # Plot 1: Volumetric Flow Rate
    ax1.step(times[:-1], flows, where="post", linewidth=2, label="Actual Flow")
    ax1.axhline(
        hotend.max_volumetric_flow,
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Hotend Limit ({hotend.max_volumetric_flow} mm³/s)",
    )
    ax1.axhline(
        hotend.max_volumetric_flow * HIGH_FLOW_THRESHOLD_RATIO,
        color="orange",
        linestyle=":",
        linewidth=1.5,
        label=f"High Flow Threshold ({HIGH_FLOW_THRESHOLD_RATIO:.0%})",
    )

    # Highlight violation regions
    for i, (t, flow, violation) in enumerate(zip(times[:-1], flows, violations)):
        if violation:
            seg_duration = times[i + 1] - t
            ax1.axvspan(t, t + seg_duration, color="red", alpha=0.15)

    ax1.set_ylabel("Volumetric Flow (mm³/s)", fontsize=11)
    ax1.legend(loc="upper right")
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(bottom=0)

    # Add violation count text
    violation_count = sum(violations)
    if violation_count > 0:
        ax1.text(
            0.02,
            0.98,
            f"WARNING: {violation_count} segments exceed hotend capacity",
            transform=ax1.transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="red", alpha=0.2),
        )

    # Plot 2: Feed Rate
    ax2.step(times[:-1], feed_rates, where="post", linewidth=2, color="green")
    ax2.set_ylabel("Feed Rate (mm/min)", fontsize=11)
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(bottom=0)

    # Plot 3: Look-ahead predictions
    # Simulate look-ahead buffer at different points
    buffer = LookAheadBuffer(window_size=4)
    prediction_times = []
    predicted_max_flows = []
    predicted_times_to_peak = []

    current_time = 0.0
    for i, seg in enumerate(segments):
        buffer.add_segment(seg)

        if buffer.is_full() or i == len(segments) - 1:
            prediction = predict_flow_window(buffer, hotend)
            if prediction:
                prediction_times.append(current_time)
                predicted_max_flows.append(prediction.max_flow)
                predicted_times_to_peak.append(prediction.time_to_peak)

        current_time += seg.travel_time()

    ax3.plot(
        prediction_times,
        predicted_max_flows,
        "o-",
        linewidth=2,
        markersize=6,
        label="Predicted Peak Flow in Window",
    )
    ax3.axhline(
        hotend.max_volumetric_flow,
        color="red",
        linestyle="--",
        linewidth=2,
        label="Hotend Limit",
    )
    ax3.set_ylabel("Predicted Flow (mm³/s)", fontsize=11)
    ax3.set_xlabel("Time (seconds)", fontsize=11)
    ax3.legend(loc="upper right")
    ax3.grid(True, alpha=0.3)
    ax3.set_ylim(bottom=0)

    # Add info text box
    info_text = f"""Material: {material.name} (Shore {material.shore_hardness})
Hotend Response: {hotend.response_time}s
Segments: {len(segments)}
Total Time: {times[-1]:.1f}s"""

    fig.text(
        0.02,
        0.02,
        info_text,
        fontsize=9,
        verticalalignment="bottom",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.3),
    )

    plt.tight_layout()
    return fig


def main():
    """Run flow analysis visualization."""
    # Create test scenario
    segments = create_test_segments()

    # Configure hotend and material
    hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
    material = MaterialConfig(name="TPU Shore 30", shore_hardness=30)

    print("Flow Analysis Visualization")
    print("=" * 50)
    print(f"Hotend: {hotend.max_volumetric_flow} mm³/s max flow")
    print(f"Material: {material.name}")
    print(f"Segments: {len(segments)}")
    print()

    # Analyze segments
    times, flows, feed_rates, violations = analyze_segments(segments, hotend)

    # Print summary
    violation_count = sum(violations)
    max_flow = max(flows)
    avg_flow = sum(f for f in flows if f > 0) / sum(1 for f in flows if f > 0)

    print(f"Max flow: {max_flow:.2f} mm³/s")
    print(f"Avg flow (excluding travel): {avg_flow:.2f} mm³/s")
    print(f"Segments exceeding limit: {violation_count}/{len(segments)}")
    print(
        f"Over-capacity by: {(max_flow - hotend.max_volumetric_flow):.2f} mm³/s "
        f"({(max_flow / hotend.max_volumetric_flow - 1) * 100:.1f}%)"
    )
    print()
    print("Creating visualization...")

    # Create plot
    plot_flow_analysis(segments, hotend, material)

    # Save to file
    output_file = "flow_analysis.png"
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    print(f"[OK] Saved to {output_file}")
    print(f"[OK] Open {output_file} to view the analysis")


if __name__ == "__main__":
    main()
