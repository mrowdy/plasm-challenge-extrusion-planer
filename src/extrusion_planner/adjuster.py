"""Feed rate adjustment for flow control."""

from typing import List

from extrusion_planner.flow_calculator import calculate_volumetric_flow
from extrusion_planner.lookahead import LookAheadBuffer, predict_flow_window
from extrusion_planner.models.hotend import HotendConfig
from extrusion_planner.models.segment import SECONDS_PER_MINUTE, Segment


def limit_feed_rate(segment: Segment, hotend: HotendConfig) -> Segment:
    """Limit feed rate to stay within hotend flow capacity."""
    if segment.extrusion == 0:
        return segment

    current_flow = calculate_volumetric_flow(segment)
    if current_flow <= hotend.max_volumetric_flow:
        return segment

    # Derive max feed rate from volumetric flow formula:
    # flow = extrusion / time, where time = (length / feed_rate) * SECONDS_PER_MINUTE
    # Solving for feed_rate: feed_rate = (flow * length * SECONDS_PER_MINUTE) / extrusion
    max_feed_rate = (
        hotend.max_volumetric_flow * segment.length * SECONDS_PER_MINUTE
    ) / segment.extrusion

    return Segment(
        length=segment.length,
        feed_rate=max_feed_rate,
        extrusion=segment.extrusion,
    )


# Number of segments before peak to begin gradual slowdown
PREEMPTIVE_RAMPDOWN_SEGMENTS = 3


def apply_preemptive_slowdown(
    segments: List[Segment], window_size: int, hotend: HotendConfig
) -> List[Segment]:
    """Apply gradual feed rate slowdown before high-flow regions."""
    if not segments:
        return []

    buffer = LookAheadBuffer(window_size=window_size)
    adjusted = []
    slowdown_plan = {}

    for i, segment in enumerate(segments):
        buffer.add_segment(segment)
        prediction = predict_flow_window(buffer, hotend)

        if prediction and prediction.max_flow > hotend.max_volumetric_flow:
            window = buffer.get_window()
            window_start_index = i - len(window) + 1
            peak_global_index = window_start_index + prediction.peak_segment_index
            required_slowdown = hotend.max_volumetric_flow / prediction.max_flow
            ramp_start = max(0, peak_global_index - PREEMPTIVE_RAMPDOWN_SEGMENTS)

            # Linear ramp: gradually slow from 1.0x to required_slowdown
            for ramp_idx in range(ramp_start, peak_global_index + 1):
                if ramp_idx == peak_global_index:
                    factor = required_slowdown
                else:
                    distance_from_peak = peak_global_index - ramp_idx
                    total_ramp_distance = peak_global_index - ramp_start
                    if total_ramp_distance > 0:
                        # Progress from 0.0 (far from peak) to 1.0 (at peak)
                        ramp_progress = 1.0 - (distance_from_peak / total_ramp_distance)
                        factor = 1.0 + ramp_progress * (required_slowdown - 1.0)
                    else:
                        factor = required_slowdown

                # When multiple peaks overlap, use most restrictive (minimum) slowdown
                if ramp_idx not in slowdown_plan:
                    slowdown_plan[ramp_idx] = factor
                else:
                    slowdown_plan[ramp_idx] = min(slowdown_plan[ramp_idx], factor)

    for i, segment in enumerate(segments):
        if i in slowdown_plan:
            factor = slowdown_plan[i]
            if segment.extrusion > 0:
                adjusted_feed = segment.feed_rate * factor
                adjusted_segment = Segment(
                    length=segment.length,
                    feed_rate=adjusted_feed,
                    extrusion=segment.extrusion,
                )
                adjusted.append(adjusted_segment)
            else:
                adjusted.append(segment)
        else:
            adjusted.append(segment)

    return adjusted
