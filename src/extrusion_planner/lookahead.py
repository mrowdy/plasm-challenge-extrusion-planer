"""Look-ahead buffer for segment analysis."""

from collections import deque
from dataclasses import dataclass
from typing import List

from extrusion_planner.flow_calculator import calculate_volumetric_flow
from extrusion_planner.models.hotend import HotendConfig
from extrusion_planner.models.segment import Segment


class LookAheadBuffer:
    """Sliding window buffer for look-ahead segment analysis."""

    def __init__(self, window_size: int) -> None:
        """Initialize look-ahead buffer with fixed window size."""
        if window_size <= 0:
            raise ValueError(f"window_size must be positive, got {window_size}")
        self._window_size = window_size
        self._buffer: deque[Segment] = deque(maxlen=window_size)

    @property
    def window_size(self) -> int:
        """Get window size."""
        return self._window_size

    def add_segment(self, segment: Segment) -> None:
        """Add segment to buffer (auto-evicts oldest if full)."""
        self._buffer.append(segment)

    def get_window(self) -> List[Segment]:
        """Get current window as list."""
        return list(self._buffer)

    def advance(self) -> None:
        """Remove oldest segment from buffer."""
        if self._buffer:
            self._buffer.popleft()

    def __len__(self) -> int:
        """Get current buffer length."""
        return len(self._buffer)

    def is_full(self) -> bool:
        """Check if buffer is at max capacity."""
        return len(self._buffer) == self._window_size

    def clear(self) -> None:
        """Remove all segments from buffer."""
        self._buffer.clear()


@dataclass(frozen=True)
class FlowPrediction:
    """Flow prediction analysis results."""

    max_flow: float
    time_to_peak: float
    high_flow_duration: float
    peak_segment_index: int


# Flow above 80% of hotend limit is considered "high flow"
HIGH_FLOW_THRESHOLD_RATIO = 0.8


def predict_flow_window(buffer: LookAheadBuffer, hotend: HotendConfig) -> FlowPrediction | None:
    """Predict flow requirements across look-ahead window."""
    window = buffer.get_window()
    if not window:
        return None

    flows: List[float] = []
    cumulative_times: List[float] = []
    current_time = 0.0

    for segment in window:
        flows.append(calculate_volumetric_flow(segment))
        cumulative_times.append(current_time)
        current_time += segment.travel_time()

    max_flow = max(flows)
    peak_index = flows.index(max_flow)
    time_to_peak = cumulative_times[peak_index]

    # High flow duration: sum of time spent above 80% of hotend capacity
    high_flow_threshold = hotend.max_volumetric_flow * HIGH_FLOW_THRESHOLD_RATIO
    high_flow_duration = sum(
        window[i].travel_time() for i, flow in enumerate(flows) if flow >= high_flow_threshold
    )

    return FlowPrediction(
        max_flow=max_flow,
        time_to_peak=time_to_peak,
        high_flow_duration=high_flow_duration,
        peak_segment_index=peak_index,
    )
