"""Feed rate adjustment functions for flow control."""

from typing import List

from extrusion_planner.flow_calculator import calculate_volumetric_flow
from extrusion_planner.lookahead import LookAheadBuffer, predict_flow_window
from extrusion_planner.models.hotend import HotendConfig
from extrusion_planner.models.segment import SECONDS_PER_MINUTE, Segment


def limit_feed_rate(segment: Segment, hotend: HotendConfig) -> Segment:
    """
    Limit segment feed rate to stay within hotend's volumetric flow capacity.

    If the segment's current flow rate exceeds the hotend's max_volumetric_flow,
    the feed rate is reduced to the maximum safe value. Otherwise, the segment
    is returned unchanged.

    Args:
        segment: Segment to potentially adjust
        hotend: Hotend configuration with max_volumetric_flow limit

    Returns:
        Original segment if flow is acceptable, or new segment with reduced
        feed rate if flow exceeds limit. Travel moves (extrusion=0) are always
        returned unchanged.

    Note:
        The maximum safe feed rate is calculated as:
        max_feed_rate = (hotend.max_flow * segment.length * 60) / segment.extrusion

        This ensures: flow = (extrusion * feed_rate) / (length * 60) <= max_flow
    """
    # Travel moves don't need adjustment
    if segment.extrusion == 0:
        return segment

    # Check if current flow exceeds limit
    current_flow = calculate_volumetric_flow(segment)
    if current_flow <= hotend.max_volumetric_flow:
        return segment

    # Calculate maximum safe feed rate
    # Flow formula: (extrusion * feed_rate) / (length * 60) = flow
    # Solving for feed_rate: feed_rate = (flow * length * 60) / extrusion
    max_feed_rate = (
        hotend.max_volumetric_flow * segment.length * SECONDS_PER_MINUTE
    ) / segment.extrusion

    # Create new segment with limited feed rate
    return Segment(
        length=segment.length,
        feed_rate=max_feed_rate,
        extrusion=segment.extrusion,
    )


# Number of segments to ramp down feed rate before peak
PREEMPTIVE_RAMPDOWN_SEGMENTS = 3


def apply_preemptive_slowdown(
    segments: List[Segment], window_size: int, hotend: HotendConfig
) -> List[Segment]:
    """
    Apply preemptive feed rate slowdown before high-flow regions.

    Uses look-ahead analysis to detect upcoming flow peaks and gradually
    reduces feed rates over the preceding segments to avoid sudden flow
    spikes that could cause under-extrusion.

    Args:
        segments: List of segments to process
        window_size: Number of segments to look ahead for flow prediction
        hotend: Hotend configuration with max_volumetric_flow limit

    Returns:
        List of segments with adjusted feed rates. Segments are modified
        only when high flow is predicted ahead. The adjustment creates a
        smooth ramp-down over PREEMPTIVE_RAMPDOWN_SEGMENTS segments before
        the predicted peak.

    Algorithm:
        1. For each segment, analyze the upcoming window for flow peaks
        2. If peak flow exceeds hotend limit and is ahead in the window:
           - Calculate required slowdown factor
           - Apply gradual ramp-down to current and upcoming segments
           - Ramp uses linear interpolation for smoothness
        3. Segments already at safe flow rates are not adjusted

    Note:
        This function handles preemptive adjustments only. Segments at the
        peak should also be processed with limit_feed_rate() to enforce
        strict flow limits.
    """
    if not segments:
        return []

    # Initialize buffer and results
    buffer = LookAheadBuffer(window_size=window_size)
    adjusted = []
    slowdown_plan = {}  # Maps segment index to slowdown factor

    # Process each segment
    for i, segment in enumerate(segments):
        buffer.add_segment(segment)

        # Predict flow in upcoming window
        prediction = predict_flow_window(buffer, hotend)

        if prediction and prediction.max_flow > hotend.max_volumetric_flow:
            # High flow detected in window
            # Calculate where the peak is in the global segment list
            window = buffer.get_window()
            window_start_index = i - len(window) + 1
            peak_global_index = window_start_index + prediction.peak_segment_index

            # Calculate how much slowdown is needed at the peak
            required_slowdown = hotend.max_volumetric_flow / prediction.max_flow

            # Apply ramp-down to segments leading up to and including peak
            # Ramp starts PREEMPTIVE_RAMPDOWN_SEGMENTS before the peak
            ramp_start = max(0, peak_global_index - PREEMPTIVE_RAMPDOWN_SEGMENTS)

            for ramp_idx in range(ramp_start, peak_global_index + 1):
                # Calculate ramp factor (linear interpolation from 1.0 to slowdown)
                if ramp_idx == peak_global_index:
                    # At peak: full slowdown
                    factor = required_slowdown
                else:
                    # Before peak: interpolate
                    distance_from_peak = peak_global_index - ramp_idx
                    total_ramp_distance = peak_global_index - ramp_start
                    if total_ramp_distance > 0:
                        ramp_progress = 1.0 - (distance_from_peak / total_ramp_distance)
                        factor = 1.0 + ramp_progress * (required_slowdown - 1.0)
                    else:
                        factor = required_slowdown

                # Update slowdown plan (use minimum factor if multiple peaks detected)
                if ramp_idx not in slowdown_plan:
                    slowdown_plan[ramp_idx] = factor
                else:
                    slowdown_plan[ramp_idx] = min(slowdown_plan[ramp_idx], factor)

    # Apply adjustments
    for i, segment in enumerate(segments):
        if i in slowdown_plan:
            factor = slowdown_plan[i]
            # Only adjust printing segments (not travel moves)
            if segment.extrusion > 0:
                adjusted_feed = segment.feed_rate * factor
                adjusted_segment = Segment(
                    length=segment.length,
                    feed_rate=adjusted_feed,
                    extrusion=segment.extrusion,
                )
                adjusted.append(adjusted_segment)
            else:
                # Travel moves unchanged
                adjusted.append(segment)
        else:
            # No adjustment needed
            adjusted.append(segment)

    return adjusted

