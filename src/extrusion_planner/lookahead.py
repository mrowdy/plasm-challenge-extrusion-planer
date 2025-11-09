"""Look-ahead buffer for analyzing upcoming segments."""

from collections import deque
from dataclasses import dataclass
from typing import List

from extrusion_planner.flow_calculator import calculate_volumetric_flow
from extrusion_planner.models.hotend import HotendConfig
from extrusion_planner.models.segment import Segment


class LookAheadBuffer:
    """
    Sliding window buffer for look-ahead analysis of extrusion segments.

    Maintains a fixed-size window of segments to enable prediction of upcoming
    flow requirements and preemptive feed rate adjustments.
    """

    def __init__(self, window_size: int) -> None:
        """
        Initialize look-ahead buffer.

        Args:
            window_size: Maximum number of segments to keep in window

        Raises:
            ValueError: If window_size is not positive
        """
        if window_size <= 0:
            raise ValueError(f"window_size must be positive, got {window_size}")

        self._window_size = window_size
        self._buffer: deque[Segment] = deque(maxlen=window_size)

    @property
    def window_size(self) -> int:
        """Get the configured window size."""
        return self._window_size

    def add_segment(self, segment: Segment) -> None:
        """
        Add a segment to the buffer.

        If buffer is at capacity, the oldest segment is automatically removed.

        Args:
            segment: Segment to add to buffer
        """
        self._buffer.append(segment)

    def get_window(self) -> List[Segment]:
        """
        Get current window of segments.

        Returns:
            List of segments in the window (may be less than window_size
            if buffer is not yet full)
        """
        return list(self._buffer)

    def advance(self) -> None:
        """
        Advance window by removing the oldest segment.

        If buffer is empty, this is a no-op.
        """
        if self._buffer:
            self._buffer.popleft()

    def __len__(self) -> int:
        """Get the current number of segments in the buffer."""
        return len(self._buffer)

    def is_full(self) -> bool:
        """Check if buffer has reached window_size capacity."""
        return len(self._buffer) == self._window_size

    def clear(self) -> None:
        """Remove all segments from the buffer."""
        self._buffer.clear()


@dataclass(frozen=True)
class FlowPrediction:
    """
    Results of flow prediction analysis over a window of segments.

    Attributes:
        max_flow: Maximum volumetric flow rate in the window (mm³/s)
        time_to_peak: Time from current position until max flow occurs (seconds)
        high_flow_duration: Duration of high flow period (seconds)
        peak_segment_index: Index of segment with maximum flow in the window
    """

    max_flow: float
    time_to_peak: float
    high_flow_duration: float
    peak_segment_index: int


# Threshold for considering flow as "high" (80% of hotend limit)
HIGH_FLOW_THRESHOLD_RATIO = 0.8


def predict_flow_window(
    buffer: LookAheadBuffer, hotend: HotendConfig
) -> FlowPrediction | None:
    """
    Predict flow requirements across the look-ahead window.

    Analyzes all segments in the buffer's current window to identify peak flow
    rates and high-flow regions that may require preemptive feed rate adjustment.

    Args:
        buffer: LookAheadBuffer containing segments to analyze
        hotend: Hotend configuration with max_volumetric_flow limit

    Returns:
        FlowPrediction with max flow, time to peak, and high flow duration,
        or None if the buffer is empty

    Note:
        "High flow" is defined as flow exceeding 80% of hotend's max_volumetric_flow.
        This threshold determines the duration calculation.
    """
    window = buffer.get_window()

    if not window:
        return None

    # Calculate flow for each segment and track cumulative time
    flows: List[float] = []
    cumulative_times: List[float] = []
    current_time = 0.0

    for segment in window:
        flows.append(calculate_volumetric_flow(segment))
        cumulative_times.append(current_time)
        current_time += segment.travel_time()

    # Find the peak flow
    max_flow = max(flows)
    peak_index = flows.index(max_flow)
    time_to_peak = cumulative_times[peak_index]

    # Calculate duration of high flow (flow > threshold)
    high_flow_threshold = hotend.max_volumetric_flow * HIGH_FLOW_THRESHOLD_RATIO
    high_flow_duration = 0.0

    for i, flow in enumerate(flows):
        if flow >= high_flow_threshold:
            high_flow_duration += window[i].travel_time()

    return FlowPrediction(
        max_flow=max_flow,
        time_to_peak=time_to_peak,
        high_flow_duration=high_flow_duration,
        peak_segment_index=peak_index,
    )
