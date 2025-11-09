"""Tests for look-ahead buffer."""

import pytest

from extrusion_planner.lookahead import (
    HIGH_FLOW_THRESHOLD_RATIO,
    FlowPrediction,
    LookAheadBuffer,
    predict_flow_window,
)
from extrusion_planner.models.hotend import HotendConfig
from extrusion_planner.models.segment import Segment


class TestLookAheadBuffer:
    """Tests for LookAheadBuffer class."""

    def test_buffer_initialization(self):
        """Test buffer can be created with valid window size."""
        buffer = LookAheadBuffer(window_size=3)
        assert buffer.window_size == 3
        assert len(buffer) == 0
        assert not buffer.is_full()

    def test_invalid_window_size_zero(self):
        """Test buffer raises error for zero window size."""
        with pytest.raises(ValueError, match="window_size must be positive"):
            LookAheadBuffer(window_size=0)

    def test_invalid_window_size_negative(self):
        """Test buffer raises error for negative window size."""
        with pytest.raises(ValueError, match="window_size must be positive"):
            LookAheadBuffer(window_size=-1)

    def test_add_segment_single(self):
        """Test adding a single segment to buffer."""
        buffer = LookAheadBuffer(window_size=3)
        seg = Segment(length=10.0, feed_rate=100.0, extrusion=0.5)

        buffer.add_segment(seg)

        assert len(buffer) == 1
        assert not buffer.is_full()
        window = buffer.get_window()
        assert len(window) == 1
        assert window[0] == seg

    def test_add_segments_up_to_capacity(self):
        """Test adding segments up to window capacity."""
        buffer = LookAheadBuffer(window_size=3)
        seg1 = Segment(length=10.0, feed_rate=100.0, extrusion=0.5)
        seg2 = Segment(length=15.0, feed_rate=120.0, extrusion=0.6)
        seg3 = Segment(length=20.0, feed_rate=150.0, extrusion=0.7)

        buffer.add_segment(seg1)
        buffer.add_segment(seg2)
        buffer.add_segment(seg3)

        assert len(buffer) == 3
        assert buffer.is_full()
        window = buffer.get_window()
        assert len(window) == 3
        assert window[0] == seg1
        assert window[1] == seg2
        assert window[2] == seg3

    def test_add_segment_exceeds_capacity(self):
        """Test adding segment when buffer is at capacity removes oldest."""
        buffer = LookAheadBuffer(window_size=3)
        seg1 = Segment(length=10.0, feed_rate=100.0, extrusion=0.5)
        seg2 = Segment(length=15.0, feed_rate=120.0, extrusion=0.6)
        seg3 = Segment(length=20.0, feed_rate=150.0, extrusion=0.7)
        seg4 = Segment(length=25.0, feed_rate=180.0, extrusion=0.8)

        buffer.add_segment(seg1)
        buffer.add_segment(seg2)
        buffer.add_segment(seg3)
        buffer.add_segment(seg4)  # Should remove seg1

        assert len(buffer) == 3
        assert buffer.is_full()
        window = buffer.get_window()
        assert len(window) == 3
        assert window[0] == seg2  # seg1 was removed
        assert window[1] == seg3
        assert window[2] == seg4

    def test_get_window_empty_buffer(self):
        """Test getting window from empty buffer returns empty list."""
        buffer = LookAheadBuffer(window_size=3)
        window = buffer.get_window()
        assert window == []
        assert isinstance(window, list)

    def test_get_window_returns_copy(self):
        """Test get_window returns a new list, not reference to internal buffer."""
        buffer = LookAheadBuffer(window_size=3)
        seg = Segment(length=10.0, feed_rate=100.0, extrusion=0.5)
        buffer.add_segment(seg)

        window1 = buffer.get_window()
        window2 = buffer.get_window()

        # Different list objects
        assert window1 is not window2
        # But same content
        assert window1 == window2

    def test_advance_removes_oldest_segment(self):
        """Test advance removes the oldest segment from buffer."""
        buffer = LookAheadBuffer(window_size=3)
        seg1 = Segment(length=10.0, feed_rate=100.0, extrusion=0.5)
        seg2 = Segment(length=15.0, feed_rate=120.0, extrusion=0.6)
        seg3 = Segment(length=20.0, feed_rate=150.0, extrusion=0.7)

        buffer.add_segment(seg1)
        buffer.add_segment(seg2)
        buffer.add_segment(seg3)

        buffer.advance()

        assert len(buffer) == 2
        assert not buffer.is_full()
        window = buffer.get_window()
        assert window[0] == seg2  # seg1 was removed
        assert window[1] == seg3

    def test_advance_empty_buffer(self):
        """Test advance on empty buffer is a no-op."""
        buffer = LookAheadBuffer(window_size=3)
        buffer.advance()  # Should not raise error
        assert len(buffer) == 0

    def test_advance_single_element(self):
        """Test advance on buffer with single element empties it."""
        buffer = LookAheadBuffer(window_size=3)
        seg = Segment(length=10.0, feed_rate=100.0, extrusion=0.5)
        buffer.add_segment(seg)

        buffer.advance()

        assert len(buffer) == 0
        assert buffer.get_window() == []

    def test_clear_removes_all_segments(self):
        """Test clear removes all segments from buffer."""
        buffer = LookAheadBuffer(window_size=3)
        seg1 = Segment(length=10.0, feed_rate=100.0, extrusion=0.5)
        seg2 = Segment(length=15.0, feed_rate=120.0, extrusion=0.6)

        buffer.add_segment(seg1)
        buffer.add_segment(seg2)

        buffer.clear()

        assert len(buffer) == 0
        assert not buffer.is_full()
        assert buffer.get_window() == []

    def test_clear_empty_buffer(self):
        """Test clear on empty buffer is safe."""
        buffer = LookAheadBuffer(window_size=3)
        buffer.clear()  # Should not raise error
        assert len(buffer) == 0

    def test_window_size_one(self):
        """Test buffer with window_size of 1 works correctly."""
        buffer = LookAheadBuffer(window_size=1)
        seg1 = Segment(length=10.0, feed_rate=100.0, extrusion=0.5)
        seg2 = Segment(length=15.0, feed_rate=120.0, extrusion=0.6)

        buffer.add_segment(seg1)
        assert len(buffer) == 1
        assert buffer.is_full()
        assert buffer.get_window()[0] == seg1

        buffer.add_segment(seg2)  # Should replace seg1
        assert len(buffer) == 1
        assert buffer.is_full()
        assert buffer.get_window()[0] == seg2

    def test_large_window_size(self):
        """Test buffer with large window size."""
        buffer = LookAheadBuffer(window_size=100)
        segments = [Segment(length=float(i), feed_rate=100.0, extrusion=0.5) for i in range(1, 51)]

        for seg in segments:
            buffer.add_segment(seg)

        assert len(buffer) == 50
        assert not buffer.is_full()
        window = buffer.get_window()
        assert len(window) == 50
        assert window == segments

    def test_sliding_window_behavior(self):
        """Test buffer maintains sliding window as segments are added and advanced."""
        buffer = LookAheadBuffer(window_size=3)
        segments = [Segment(length=float(i), feed_rate=100.0, extrusion=0.5) for i in range(1, 6)]

        # Fill buffer
        buffer.add_segment(segments[0])
        buffer.add_segment(segments[1])
        buffer.add_segment(segments[2])
        assert buffer.get_window() == segments[0:3]

        # Advance and add new segment
        buffer.advance()
        buffer.add_segment(segments[3])
        assert buffer.get_window() == segments[1:4]

        # Advance and add another
        buffer.advance()
        buffer.add_segment(segments[4])
        assert buffer.get_window() == segments[2:5]

    def test_travel_move_segments(self):
        """Test buffer works with travel move segments (extrusion=0)."""
        buffer = LookAheadBuffer(window_size=3)
        travel = Segment(length=50.0, feed_rate=300.0, extrusion=0.0)
        print_seg = Segment(length=10.0, feed_rate=100.0, extrusion=0.5)

        buffer.add_segment(travel)
        buffer.add_segment(print_seg)

        assert len(buffer) == 2
        window = buffer.get_window()
        assert window[0].extrusion == 0.0
        assert window[1].extrusion == 0.5


class TestPredictFlowWindow:
    """Tests for predict_flow_window function."""

    def test_empty_buffer_returns_none(self):
        """Test prediction on empty buffer returns None."""
        buffer = LookAheadBuffer(window_size=3)
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)

        result = predict_flow_window(buffer, hotend)

        assert result is None

    def test_single_segment_prediction(self):
        """Test prediction with single segment in buffer."""
        buffer = LookAheadBuffer(window_size=3)
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        # length=10, feed_rate=100 -> travel_time=6s
        # To get 3 mm³/s: extrusion = 3 * 6 = 18 mm³
        seg = Segment(length=10.0, feed_rate=100.0, extrusion=18.0)  # 3 mm³/s

        buffer.add_segment(seg)
        result = predict_flow_window(buffer, hotend)

        assert result is not None
        assert result.max_flow == pytest.approx(3.0, rel=0.01)
        assert result.time_to_peak == 0.0  # First segment
        assert result.peak_segment_index == 0

    def test_peak_at_first_segment(self):
        """Test when peak flow is in the first segment."""
        buffer = LookAheadBuffer(window_size=3)
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        # seg1: travel_time=2s, flow=15 mm³/s -> extrusion=30
        # seg2: travel_time=6s, flow=3 mm³/s -> extrusion=18
        # seg3: travel_time=6s, flow=2 mm³/s -> extrusion=12
        seg1 = Segment(length=5.0, feed_rate=150.0, extrusion=30.0)  # 15 mm³/s
        seg2 = Segment(length=10.0, feed_rate=100.0, extrusion=18.0)  # 3 mm³/s
        seg3 = Segment(length=10.0, feed_rate=100.0, extrusion=12.0)  # 2 mm³/s

        buffer.add_segment(seg1)
        buffer.add_segment(seg2)
        buffer.add_segment(seg3)
        result = predict_flow_window(buffer, hotend)

        assert result is not None
        assert result.max_flow == pytest.approx(15.0, rel=0.01)
        assert result.time_to_peak == 0.0  # Peak is at start
        assert result.peak_segment_index == 0

    def test_peak_at_middle_segment(self):
        """Test when peak flow is in a middle segment."""
        buffer = LookAheadBuffer(window_size=3)
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        seg1 = Segment(length=10.0, feed_rate=100.0, extrusion=12.0)  # 2 mm³/s
        seg2 = Segment(length=5.0, feed_rate=150.0, extrusion=30.0)  # 15 mm³/s
        seg3 = Segment(length=10.0, feed_rate=100.0, extrusion=18.0)  # 3 mm³/s

        buffer.add_segment(seg1)
        buffer.add_segment(seg2)
        buffer.add_segment(seg3)
        result = predict_flow_window(buffer, hotend)

        assert result is not None
        assert result.max_flow == pytest.approx(15.0, rel=0.01)
        # Time to peak = seg1 travel time
        assert result.time_to_peak == pytest.approx(seg1.travel_time(), rel=0.01)
        assert result.peak_segment_index == 1

    def test_peak_at_last_segment(self):
        """Test when peak flow is in the last segment."""
        buffer = LookAheadBuffer(window_size=3)
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        seg1 = Segment(length=10.0, feed_rate=100.0, extrusion=12.0)  # 2 mm³/s
        seg2 = Segment(length=10.0, feed_rate=100.0, extrusion=18.0)  # 3 mm³/s
        seg3 = Segment(length=5.0, feed_rate=150.0, extrusion=30.0)  # 15 mm³/s

        buffer.add_segment(seg1)
        buffer.add_segment(seg2)
        buffer.add_segment(seg3)
        result = predict_flow_window(buffer, hotend)

        assert result is not None
        assert result.max_flow == pytest.approx(15.0, rel=0.01)
        # Time to peak = seg1 + seg2 travel times
        expected_time = seg1.travel_time() + seg2.travel_time()
        assert result.time_to_peak == pytest.approx(expected_time, rel=0.01)
        assert result.peak_segment_index == 2

    def test_high_flow_duration_all_segments_high(self):
        """Test high flow duration when all segments exceed threshold."""
        buffer = LookAheadBuffer(window_size=3)
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        # All segments above 80% of 12.0 = 9.6 mm³/s
        # travel_time=6s, flow=10 mm³/s -> extrusion=60
        seg1 = Segment(length=10.0, feed_rate=100.0, extrusion=60.0)  # 10 mm³/s
        seg2 = Segment(length=10.0, feed_rate=100.0, extrusion=60.0)  # 10 mm³/s
        seg3 = Segment(length=10.0, feed_rate=100.0, extrusion=60.0)  # 10 mm³/s

        buffer.add_segment(seg1)
        buffer.add_segment(seg2)
        buffer.add_segment(seg3)
        result = predict_flow_window(buffer, hotend)

        assert result is not None
        # All three segments are high flow
        total_duration = seg1.travel_time() + seg2.travel_time() + seg3.travel_time()
        assert result.high_flow_duration == pytest.approx(total_duration, rel=0.01)

    def test_high_flow_duration_no_segments_high(self):
        """Test high flow duration when no segments exceed threshold."""
        buffer = LookAheadBuffer(window_size=3)
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        # All segments below 80% of 12.0 = 9.6 mm³/s
        seg1 = Segment(length=10.0, feed_rate=100.0, extrusion=0.5)  # 5 mm³/s
        seg2 = Segment(length=10.0, feed_rate=100.0, extrusion=0.5)  # 5 mm³/s
        seg3 = Segment(length=10.0, feed_rate=100.0, extrusion=0.5)  # 5 mm³/s

        buffer.add_segment(seg1)
        buffer.add_segment(seg2)
        buffer.add_segment(seg3)
        result = predict_flow_window(buffer, hotend)

        assert result is not None
        assert result.high_flow_duration == 0.0

    def test_high_flow_duration_partial_segments(self):
        """Test high flow duration when only some segments are high."""
        buffer = LookAheadBuffer(window_size=4)
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        # Threshold is 9.6 mm³/s, travel_time=6s
        seg1 = Segment(length=10.0, feed_rate=100.0, extrusion=30.0)  # 5 mm³/s (low)
        seg2 = Segment(length=10.0, feed_rate=100.0, extrusion=60.0)  # 10 mm³/s (high)
        seg3 = Segment(length=10.0, feed_rate=100.0, extrusion=60.0)  # 10 mm³/s (high)
        seg4 = Segment(length=10.0, feed_rate=100.0, extrusion=30.0)  # 5 mm³/s (low)

        buffer.add_segment(seg1)
        buffer.add_segment(seg2)
        buffer.add_segment(seg3)
        buffer.add_segment(seg4)
        result = predict_flow_window(buffer, hotend)

        assert result is not None
        # Only seg2 and seg3 are high flow
        expected_duration = seg2.travel_time() + seg3.travel_time()
        assert result.high_flow_duration == pytest.approx(expected_duration, rel=0.01)

    def test_travel_move_has_zero_flow(self):
        """Test that travel moves (extrusion=0) don't contribute to peak flow."""
        buffer = LookAheadBuffer(window_size=3)
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        seg1 = Segment(length=50.0, feed_rate=300.0, extrusion=0.0)  # 0 mm³/s (travel)
        seg2 = Segment(length=10.0, feed_rate=100.0, extrusion=30.0)  # 5 mm³/s
        seg3 = Segment(length=10.0, feed_rate=100.0, extrusion=18.0)  # 3 mm³/s

        buffer.add_segment(seg1)
        buffer.add_segment(seg2)
        buffer.add_segment(seg3)
        result = predict_flow_window(buffer, hotend)

        assert result is not None
        assert result.max_flow == pytest.approx(5.0, rel=0.01)
        assert result.peak_segment_index == 1  # seg2, not the travel move

    def test_flow_prediction_dataclass_immutable(self):
        """Test that FlowPrediction is immutable."""
        prediction = FlowPrediction(
            max_flow=10.0,
            time_to_peak=0.5,
            high_flow_duration=1.0,
            peak_segment_index=2,
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            prediction.max_flow = 15.0

    def test_realistic_printing_scenario(self):
        """Test with realistic printing scenario: slow perimeter then fast infill."""
        buffer = LookAheadBuffer(window_size=4)
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        # Slow perimeter: length=20, feed_rate=40 -> travel_time=30s
        # Flow=1.3 mm³/s -> extrusion=39
        seg1 = Segment(length=20.0, feed_rate=40.0, extrusion=39.0)  # 1.3 mm³/s
        # Fast infill: length=30, feed_rate=120 -> travel_time=15s
        # Flow=10 mm³/s -> extrusion=150
        seg2 = Segment(length=30.0, feed_rate=120.0, extrusion=150.0)  # 10 mm³/s
        seg3 = Segment(length=30.0, feed_rate=120.0, extrusion=150.0)  # 10 mm³/s
        # Back to perimeter
        seg4 = Segment(length=20.0, feed_rate=40.0, extrusion=39.0)  # 1.3 mm³/s

        buffer.add_segment(seg1)
        buffer.add_segment(seg2)
        buffer.add_segment(seg3)
        buffer.add_segment(seg4)
        result = predict_flow_window(buffer, hotend)

        assert result is not None
        assert result.max_flow == pytest.approx(10.0, rel=0.01)
        # Peak is at seg2
        assert result.time_to_peak == pytest.approx(seg1.travel_time(), rel=0.01)
        assert result.peak_segment_index == 1
        # High flow is seg2 and seg3 (both >= 9.6 mm³/s)
        expected_duration = seg2.travel_time() + seg3.travel_time()
        assert result.high_flow_duration == pytest.approx(expected_duration, rel=0.01)

    def test_high_flow_threshold_constant(self):
        """Test that HIGH_FLOW_THRESHOLD_RATIO is set correctly."""
        assert HIGH_FLOW_THRESHOLD_RATIO == 0.8

    def test_multiple_peaks_same_value(self):
        """Test when multiple segments have the same peak flow."""
        buffer = LookAheadBuffer(window_size=3)
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        # travel_time=6s
        seg1 = Segment(length=10.0, feed_rate=100.0, extrusion=60.0)  # 10 mm³/s
        seg2 = Segment(length=10.0, feed_rate=100.0, extrusion=60.0)  # 10 mm³/s
        seg3 = Segment(length=10.0, feed_rate=100.0, extrusion=30.0)  # 5 mm³/s

        buffer.add_segment(seg1)
        buffer.add_segment(seg2)
        buffer.add_segment(seg3)
        result = predict_flow_window(buffer, hotend)

        assert result is not None
        assert result.max_flow == pytest.approx(10.0, rel=0.01)
        # Should return the first peak
        assert result.time_to_peak == 0.0
        assert result.peak_segment_index == 0
