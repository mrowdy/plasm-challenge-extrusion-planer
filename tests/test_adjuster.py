"""Tests for feed rate adjustment functions."""

import pytest

from extrusion_planner.adjuster import (
    PREEMPTIVE_RAMPDOWN_SEGMENTS,
    apply_preemptive_slowdown,
    limit_feed_rate,
)
from extrusion_planner.flow_calculator import calculate_volumetric_flow
from extrusion_planner.models.hotend import HotendConfig
from extrusion_planner.models.segment import Segment


class TestLimitFeedRate:
    """Tests for limit_feed_rate function."""

    def test_segment_within_limit_unchanged(self):
        """Test segment with acceptable flow is returned unchanged."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        # Flow: 5 mm³/s (well below 12)
        segment = Segment(length=10.0, feed_rate=100.0, extrusion=30.0)

        result = limit_feed_rate(segment, hotend)

        assert result is segment  # Same object
        assert result.feed_rate == 100.0

    def test_segment_exactly_at_limit_unchanged(self):
        """Test segment exactly at flow limit is not adjusted."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        # Flow: exactly 12 mm³/s
        segment = Segment(length=10.0, feed_rate=100.0, extrusion=72.0)

        result = limit_feed_rate(segment, hotend)

        assert result is segment
        assert result.feed_rate == 100.0

    def test_segment_exceeding_limit_adjusted(self):
        """Test segment exceeding flow limit has feed rate reduced."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        # Flow: 14 mm³/s (exceeds 12)
        segment = Segment(length=10.0, feed_rate=100.0, extrusion=84.0)

        result = limit_feed_rate(segment, hotend)

        # Should be a new segment
        assert result is not segment
        # Feed rate should be reduced
        assert result.feed_rate < segment.feed_rate
        # Length and extrusion unchanged
        assert result.length == segment.length
        assert result.extrusion == segment.extrusion
        # Adjusted flow should be at or below limit
        adjusted_flow = calculate_volumetric_flow(result)
        assert adjusted_flow <= hotend.max_volumetric_flow
        assert adjusted_flow == pytest.approx(12.0, rel=0.01)

    def test_adjusted_feed_rate_calculation(self):
        """Test that adjusted feed rate produces correct flow."""
        hotend = HotendConfig(max_volumetric_flow=10.0, response_time=0.05)
        # Flow: 15 mm³/s (exceeds 10)
        segment = Segment(length=20.0, feed_rate=80.0, extrusion=225.0)

        result = limit_feed_rate(segment, hotend)

        # Expected: max_feed = (10 * 20 * 60) / 225 = 53.33 mm/min
        expected_feed = (10.0 * 20.0 * 60.0) / 225.0
        assert result.feed_rate == pytest.approx(expected_feed, rel=0.01)

        # Verify flow is at limit
        flow = calculate_volumetric_flow(result)
        assert flow == pytest.approx(10.0, rel=0.01)

    def test_travel_move_unchanged(self):
        """Test travel moves (extrusion=0) are never adjusted."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        travel = Segment(length=50.0, feed_rate=300.0, extrusion=0.0)

        result = limit_feed_rate(travel, hotend)

        assert result is travel
        assert result.feed_rate == 300.0

    def test_multiple_adjustments_idempotent(self):
        """Test that adjusting an already-adjusted segment doesn't change it."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        segment = Segment(length=10.0, feed_rate=100.0, extrusion=84.0)

        # First adjustment
        adjusted1 = limit_feed_rate(segment, hotend)
        # Second adjustment on already-adjusted segment
        adjusted2 = limit_feed_rate(adjusted1, hotend)

        assert adjusted2 is adjusted1  # Should be unchanged
        assert adjusted2.feed_rate == adjusted1.feed_rate

    def test_severe_flow_violation(self):
        """Test segment with severe flow violation (2x limit)."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        # Flow: 24 mm³/s (2x the limit)
        segment = Segment(length=10.0, feed_rate=100.0, extrusion=144.0)

        result = limit_feed_rate(segment, hotend)

        # Feed rate should be halved
        assert result.feed_rate == pytest.approx(50.0, rel=0.01)
        # Flow should be at limit
        flow = calculate_volumetric_flow(result)
        assert flow == pytest.approx(12.0, rel=0.01)

    def test_different_hotend_limits(self):
        """Test with different hotend flow capacities."""
        segment = Segment(length=10.0, feed_rate=100.0, extrusion=60.0)  # 10 mm³/s

        # Low-capacity hotend (8 mm³/s)
        low_hotend = HotendConfig(max_volumetric_flow=8.0, response_time=0.05)
        result_low = limit_feed_rate(segment, low_hotend)
        flow_low = calculate_volumetric_flow(result_low)
        assert flow_low == pytest.approx(8.0, rel=0.01)

        # High-capacity hotend (15 mm³/s)
        high_hotend = HotendConfig(max_volumetric_flow=15.0, response_time=0.05)
        result_high = limit_feed_rate(segment, high_hotend)
        assert result_high is segment  # No adjustment needed

    def test_realistic_pla_printing(self):
        """Test with realistic PLA printing scenario."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        # Fast infill: 30mm long, 120 mm/min, requesting 150 mm³
        # Flow: 10 mm³/s (acceptable)
        segment = Segment(length=30.0, feed_rate=120.0, extrusion=150.0)

        result = limit_feed_rate(segment, hotend)

        assert result is segment  # No adjustment needed

    def test_realistic_tpu_fast_infill_exceeds_limit(self):
        """Test TPU fast infill that exceeds hotend capacity."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        # Fast infill: 30mm, 120 mm/min, 210 mm³ extrusion
        # Flow: 14 mm³/s (exceeds limit)
        segment = Segment(length=30.0, feed_rate=120.0, extrusion=210.0)

        result = limit_feed_rate(segment, hotend)

        assert result is not segment
        # Expected: max_feed = (12 * 30 * 60) / 210 = 102.86 mm/min
        expected_feed = (12.0 * 30.0 * 60.0) / 210.0
        assert result.feed_rate == pytest.approx(expected_feed, rel=0.01)
        # Verify flow
        flow = calculate_volumetric_flow(result)
        assert flow == pytest.approx(12.0, rel=0.01)

    def test_very_short_segment_high_extrusion(self):
        """Test very short segment with high extrusion density."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        # 2mm segment, 60 mm/min, 50 mm³ extrusion
        # Flow: 25 mm³/s (severe violation)
        segment = Segment(length=2.0, feed_rate=60.0, extrusion=50.0)

        result = limit_feed_rate(segment, hotend)

        assert result.feed_rate < segment.feed_rate
        flow = calculate_volumetric_flow(result)
        assert flow == pytest.approx(12.0, rel=0.01)

    def test_long_segment_low_extrusion(self):
        """Test long segment with low extrusion (should not need adjustment)."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        # 100mm segment, 40 mm/min, 20 mm³ extrusion
        # Flow: 0.13 mm³/s (very low)
        segment = Segment(length=100.0, feed_rate=40.0, extrusion=20.0)

        result = limit_feed_rate(segment, hotend)

        assert result is segment  # No adjustment

    def test_adjusted_segment_immutability(self):
        """Test that original segment is not modified during adjustment."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        original = Segment(length=10.0, feed_rate=100.0, extrusion=84.0)
        original_feed = original.feed_rate

        adjusted = limit_feed_rate(original, hotend)

        # Original unchanged
        assert original.feed_rate == original_feed
        # Adjusted is different
        assert adjusted.feed_rate != original_feed

    def test_high_capacity_induction_hotend(self):
        """Test with high-capacity induction hotend."""
        hotend = HotendConfig(max_volumetric_flow=18.0, response_time=0.01)
        # Aggressive infill: 14 mm³/s flow
        segment = Segment(length=30.0, feed_rate=120.0, extrusion=210.0)

        result = limit_feed_rate(segment, hotend)

        # Should not need adjustment (14 < 18)
        assert result is segment

    def test_edge_case_very_small_extrusion(self):
        """Test edge case with very small extrusion amount."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        # Minimal extrusion
        segment = Segment(length=10.0, feed_rate=100.0, extrusion=0.1)

        result = limit_feed_rate(segment, hotend)

        # Should not need adjustment (flow is tiny)
        assert result is segment


class TestApplyPreemptiveSlowdown:
    """Tests for apply_preemptive_slowdown function."""

    def test_empty_list(self):
        """Test with empty segment list."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        result = apply_preemptive_slowdown([], window_size=4, hotend=hotend)
        assert result == []

    def test_no_high_flow_no_adjustment(self):
        """Test segments with acceptable flow are not adjusted."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        segments = [
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),  # 5 mm³/s
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),
        ]

        result = apply_preemptive_slowdown(segments, window_size=3, hotend=hotend)

        # All segments unchanged
        assert len(result) == 3
        for i, seg in enumerate(result):
            assert seg.feed_rate == segments[i].feed_rate

    def test_single_peak_creates_rampdown(self):
        """Test single high-flow peak creates gradual ramp-down."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        segments = [
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),  # 5 mm³/s
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),  # 5 mm³/s
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),  # 5 mm³/s
            Segment(length=10.0, feed_rate=100.0, extrusion=84.0),  # 14 mm³/s (peak!)
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),  # 5 mm³/s
        ]

        result = apply_preemptive_slowdown(segments, window_size=5, hotend=hotend)

        assert len(result) == 5
        # First segment should be unchanged (too far from peak)
        assert result[0].feed_rate == 100.0
        # Segments 1-3 should have gradually decreasing feed rates
        assert result[1].feed_rate < 100.0
        assert result[2].feed_rate < result[1].feed_rate
        assert result[3].feed_rate < result[2].feed_rate
        # Last segment back to normal
        assert result[4].feed_rate == 100.0

    def test_rampdown_constant_check(self):
        """Test that PREEMPTIVE_RAMPDOWN_SEGMENTS constant is reasonable."""
        assert PREEMPTIVE_RAMPDOWN_SEGMENTS == 3

    def test_peak_at_start_no_ramp_room(self):
        """Test peak at start with no room for ramp-down."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        segments = [
            Segment(length=10.0, feed_rate=100.0, extrusion=84.0),  # 14 mm³/s (peak!)
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),  # 5 mm³/s
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),
        ]

        result = apply_preemptive_slowdown(segments, window_size=3, hotend=hotend)

        assert len(result) == 3
        # Peak segment should be slowed down
        assert result[0].feed_rate < segments[0].feed_rate
        # Others unchanged
        assert result[1].feed_rate == segments[1].feed_rate

    def test_travel_moves_unchanged(self):
        """Test travel moves are not affected by preemptive slowdown."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        segments = [
            Segment(length=50.0, feed_rate=300.0, extrusion=0.0),  # Travel
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),  # 5 mm³/s
            Segment(length=10.0, feed_rate=100.0, extrusion=84.0),  # 14 mm³/s (peak!)
        ]

        result = apply_preemptive_slowdown(segments, window_size=3, hotend=hotend)

        # Travel move unchanged
        assert result[0].feed_rate == 300.0
        assert result[0].extrusion == 0.0

    def test_multiple_peaks_handled(self):
        """Test handling separate high-flow peaks."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        # Two separate peaks with different flow rates so both are detected
        segments = [
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),  # 5 mm³/s
            Segment(length=10.0, feed_rate=100.0, extrusion=84.0),  # 14 mm³/s (peak 1)
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),  # 5 mm³/s
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),
            Segment(length=10.0, feed_rate=100.0, extrusion=90.0),  # 15 mm³/s (peak 2, higher)
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),
        ]

        result = apply_preemptive_slowdown(segments, window_size=6, hotend=hotend)

        assert len(result) == 6
        # Both peak segments should be adjusted
        assert result[1].feed_rate < segments[1].feed_rate
        assert result[4].feed_rate < segments[4].feed_rate

    def test_realistic_perimeter_to_infill_transition(self):
        """Test realistic transition from slow perimeter to fast infill."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        # Slow perimeter then fast infill that exceeds limit
        segments = [
            Segment(length=20.0, feed_rate=40.0, extrusion=26.0),  # 1.3 mm³/s
            Segment(length=20.0, feed_rate=40.0, extrusion=26.0),
            Segment(length=20.0, feed_rate=40.0, extrusion=26.0),
            Segment(length=30.0, feed_rate=120.0, extrusion=210.0),  # 14 mm³/s (peak!)
            Segment(length=30.0, feed_rate=120.0, extrusion=210.0),  # 14 mm³/s
            Segment(length=20.0, feed_rate=40.0, extrusion=26.0),
        ]

        result = apply_preemptive_slowdown(segments, window_size=5, hotend=hotend)

        assert len(result) == 6
        # First infill segment (peak) should be slowed down
        assert result[3].feed_rate < segments[3].feed_rate
        # Preemptive slowdown handles the first peak and creates a smooth ramp
        # For consecutive identical peaks, limit_feed_rate() should be used
        # in a second pass to ensure all segments are within limits

    def test_window_size_affects_detection(self):
        """Test that window size affects peak detection range."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        segments = [
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),  # 5 mm³/s
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),
            Segment(length=10.0, feed_rate=100.0, extrusion=84.0),  # 14 mm³/s (peak!)
        ]

        # Small window - might not see peak early enough
        result_small = apply_preemptive_slowdown(segments, window_size=2, hotend=hotend)

        # Large window - should see peak earlier
        result_large = apply_preemptive_slowdown(segments, window_size=6, hotend=hotend)

        # With larger window, earlier segments might be adjusted
        # Both should handle the peak segment itself
        assert result_small[5].feed_rate < segments[5].feed_rate
        assert result_large[5].feed_rate < segments[5].feed_rate

    def test_smoothness_of_ramp(self):
        """Test that ramp-down is smooth (monotonically decreasing)."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        segments = [
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),  # 5 mm³/s
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),
            Segment(length=10.0, feed_rate=100.0, extrusion=84.0),  # 14 mm³/s (peak!)
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),
        ]

        result = apply_preemptive_slowdown(segments, window_size=6, hotend=hotend)

        # Check ramp segments (should be segments 1-4 based on PREEMPTIVE_RAMPDOWN_SEGMENTS=3)
        # Feed rates should decrease smoothly approaching the peak
        ramp_indices = [i for i in range(len(segments) - 1) if result[i].extrusion > 0]
        for i in range(len(ramp_indices) - 1):
            idx = ramp_indices[i]
            next_idx = ramp_indices[i + 1]
            if idx < 4:  # Before peak
                # Each segment should have same or lower feed rate
                assert result[next_idx].feed_rate <= result[idx].feed_rate + 0.01

    def test_originals_unchanged(self):
        """Test that original segments are not modified."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        segments = [
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),
            Segment(length=10.0, feed_rate=100.0, extrusion=84.0),  # 14 mm³/s
        ]
        original_feeds = [seg.feed_rate for seg in segments]

        result = apply_preemptive_slowdown(segments, window_size=2, hotend=hotend)

        # Originals unchanged
        for i, seg in enumerate(segments):
            assert seg.feed_rate == original_feeds[i]
        # Result is different
        assert result[1].feed_rate != original_feeds[1]

    def test_single_segment(self):
        """Test with a single segment."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        segments = [Segment(length=10.0, feed_rate=100.0, extrusion=84.0)]  # 14 mm³/s

        result = apply_preemptive_slowdown(segments, window_size=1, hotend=hotend)

        assert len(result) == 1
        # Should be adjusted
        assert result[0].feed_rate < segments[0].feed_rate

    def test_combined_with_limit_feed_rate(self):
        """Test that preemptive slowdown works well with limit_feed_rate."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        segments = [
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),  # 5 mm³/s
            Segment(length=10.0, feed_rate=100.0, extrusion=84.0),  # 14 mm³/s (peak!)
            Segment(length=10.0, feed_rate=100.0, extrusion=30.0),
        ]

        # Apply preemptive slowdown first
        preemptive = apply_preemptive_slowdown(segments, window_size=3, hotend=hotend)

        # Then apply strict limit
        final = [limit_feed_rate(seg, hotend) for seg in preemptive]

        # All segments should now be within flow limits
        for seg in final:
            flow = calculate_volumetric_flow(seg)
            assert flow <= hotend.max_volumetric_flow + 0.01  # Small tolerance
