"""Tests for volumetric flow rate calculation and limit checking."""

import pytest

from extrusion_planner.flow_calculator import calculate_volumetric_flow, check_flow_limit
from extrusion_planner.models.hotend import HotendConfig
from extrusion_planner.models.segment import Segment


class TestCalculateVolumetricFlow:
    """Test cases for calculate_volumetric_flow function."""

    def test_normal_extrusion_segment(self):
        """Test flow calculation for a normal printing segment."""
        # Segment: 10mm length, 60mm/min feed rate = 10 seconds travel time
        # Extrusion: 0.5mm³ over 10 seconds = 0.05 mm³/s
        segment = Segment(length=10.0, feed_rate=60.0, extrusion=0.5)
        flow = calculate_volumetric_flow(segment)
        assert flow == pytest.approx(0.05, rel=1e-6)

    def test_travel_move_zero_flow(self):
        """Test that travel moves (extrusion=0) have zero flow."""
        travel = Segment(length=20.0, feed_rate=120.0, extrusion=0.0)
        flow = calculate_volumetric_flow(travel)
        assert flow == 0.0

    def test_high_speed_high_extrusion(self):
        """Test flow calculation for high-speed, high-extrusion segment."""
        # Fast segment: 5mm at 150mm/min = 2 seconds travel time
        # High extrusion: 0.25mm³ over 2 seconds = 0.125 mm³/s
        segment = Segment(length=5.0, feed_rate=150.0, extrusion=0.25)
        flow = calculate_volumetric_flow(segment)
        assert flow == pytest.approx(0.125, rel=1e-6)

    def test_slow_speed_low_extrusion(self):
        """Test flow calculation for slow segment with low extrusion."""
        # Slow segment: 20mm at 30mm/min = 40 seconds travel time
        # Low extrusion: 0.2mm³ over 40 seconds = 0.005 mm³/s
        segment = Segment(length=20.0, feed_rate=30.0, extrusion=0.2)
        flow = calculate_volumetric_flow(segment)
        assert flow == pytest.approx(0.005, rel=1e-6)

    def test_very_short_segment_high_flow(self):
        """Test that short segments at high speed can have high flow rates."""
        # Very short segment: 1mm at 60mm/min = 1 second travel time
        # Moderate extrusion: 0.1mm³ over 1 second = 0.1 mm³/s
        segment = Segment(length=1.0, feed_rate=60.0, extrusion=0.1)
        flow = calculate_volumetric_flow(segment)
        assert flow == pytest.approx(0.1, rel=1e-6)

    def test_realistic_pla_printing_segment(self):
        """Test flow for realistic PLA printing parameters."""
        # Typical PLA: 12mm segment at 90mm/min, 0.48mm³ extrusion
        # Travel time: (12 / 90) * 60 = 8 seconds
        # Flow: 0.48 / 8 = 0.06 mm³/s
        segment = Segment(length=12.0, feed_rate=90.0, extrusion=0.48)
        flow = calculate_volumetric_flow(segment)
        assert flow == pytest.approx(0.06, rel=1e-6)

    def test_realistic_tpu_printing_segment(self):
        """Test flow for realistic TPU printing parameters (slower)."""
        # Typical soft TPU: 10mm segment at 30mm/min, 0.3mm³ extrusion
        # Travel time: (10 / 30) * 60 = 20 seconds
        # Flow: 0.3 / 20 = 0.015 mm³/s
        segment = Segment(length=10.0, feed_rate=30.0, extrusion=0.3)
        flow = calculate_volumetric_flow(segment)
        assert flow == pytest.approx(0.015, rel=1e-6)

    def test_flow_calculation_matches_segment_method(self):
        """Verify that calculate_volumetric_flow matches Segment.extrusion_rate()."""
        segment = Segment(length=15.0, feed_rate=75.0, extrusion=0.6)
        flow_from_function = calculate_volumetric_flow(segment)
        flow_from_method = segment.extrusion_rate()
        assert flow_from_function == flow_from_method


class TestCheckFlowLimit:
    """Test cases for check_flow_limit function."""

    def test_flow_below_limit(self):
        """Test segment with flow well below hotend limit."""
        # Flow: 0.05 mm³/s, Limit: 12.0 mm³/s → should NOT exceed
        segment = Segment(length=10.0, feed_rate=60.0, extrusion=0.5)
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        assert check_flow_limit(segment, hotend) is False

    def test_flow_above_limit(self):
        """Test segment with flow exceeding hotend limit."""
        # Flow: 12.0 mm³/s (20mm³ over 10/6 seconds), Limit: 12.0 mm³/s → should exceed
        # Actually let's make it clearly above
        # Segment: 10mm at 60mm/min = 10 seconds, extrusion 200mm³
        # Flow: 200 / 10 = 20 mm³/s
        segment = Segment(length=10.0, feed_rate=60.0, extrusion=200.0)
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        assert check_flow_limit(segment, hotend) is True

    def test_flow_exactly_at_limit(self):
        """Test segment with flow exactly at hotend limit."""
        # Flow: 12.0 mm³/s exactly, Limit: 12.0 mm³/s
        # Segment: 10mm at 60mm/min = 10 seconds, extrusion 120mm³
        # Flow: 120 / 10 = 12.0 mm³/s
        segment = Segment(length=10.0, feed_rate=60.0, extrusion=120.0)
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        # At exactly the limit, it does NOT exceed (not >)
        assert check_flow_limit(segment, hotend) is False

    def test_flow_just_below_limit(self):
        """Test segment with flow just barely below limit."""
        # Flow: 11.99 mm³/s, Limit: 12.0 mm³/s → should NOT exceed
        segment = Segment(length=10.0, feed_rate=60.0, extrusion=119.9)
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        assert check_flow_limit(segment, hotend) is False

    def test_flow_just_above_limit(self):
        """Test segment with flow just barely above limit."""
        # Flow: 12.01 mm³/s, Limit: 12.0 mm³/s → should exceed
        segment = Segment(length=10.0, feed_rate=60.0, extrusion=120.1)
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        assert check_flow_limit(segment, hotend) is True

    def test_travel_move_never_exceeds_limit(self):
        """Test that travel moves (zero flow) never exceed limit."""
        travel = Segment(length=50.0, feed_rate=200.0, extrusion=0.0)
        hotend = HotendConfig(max_volumetric_flow=1.0, response_time=0.1)
        assert check_flow_limit(travel, hotend) is False

    def test_low_limit_hotend(self):
        """Test flow checking with a low-capacity hotend."""
        # Low-capacity hotend: 5.0 mm³/s limit
        # Segment with 6.0 mm³/s flow
        # Segment: 10mm at 60mm/min = 10s, extrusion 60mm³
        # Flow: 60 / 10 = 6.0 mm³/s
        segment = Segment(length=10.0, feed_rate=60.0, extrusion=60.0)
        hotend = HotendConfig(max_volumetric_flow=5.0, response_time=0.1)
        assert check_flow_limit(segment, hotend) is True

    def test_high_capacity_hotend(self):
        """Test flow checking with a high-capacity hotend."""
        # High-capacity hotend: 25.0 mm³/s limit
        # Segment with 12.0 mm³/s flow
        segment = Segment(length=10.0, feed_rate=60.0, extrusion=120.0)
        hotend = HotendConfig(max_volumetric_flow=25.0, response_time=0.02)
        assert check_flow_limit(segment, hotend) is False

    def test_realistic_scenario_pla_standard_hotend(self):
        """Test realistic PLA printing with standard hotend."""
        # PLA segment: 12mm at 90mm/min, 0.48mm³ extrusion
        # Flow: 0.06 mm³/s
        # Standard hotend: 12.0 mm³/s limit
        segment = Segment(length=12.0, feed_rate=90.0, extrusion=0.48)
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        assert check_flow_limit(segment, hotend) is False

    def test_realistic_scenario_fast_infill(self):
        """Test fast infill printing that might exceed limit."""
        # Fast infill: 5mm at 150mm/min, 0.25mm³ extrusion
        # Travel time: (5 / 150) * 60 = 2 seconds
        # Flow: 0.25 / 2 = 0.125 mm³/s
        # Low-end hotend: 0.1 mm³/s limit
        segment = Segment(length=5.0, feed_rate=150.0, extrusion=0.25)
        hotend = HotendConfig(max_volumetric_flow=0.1, response_time=0.08)
        assert check_flow_limit(segment, hotend) is True

    def test_different_hotend_response_times_same_limit(self):
        """Test that response_time doesn't affect flow limit checking."""
        # Flow limit checking should only depend on max_volumetric_flow
        segment = Segment(length=10.0, feed_rate=60.0, extrusion=100.0)

        hotend_fast = HotendConfig(max_volumetric_flow=12.0, response_time=0.02)
        hotend_slow = HotendConfig(max_volumetric_flow=12.0, response_time=0.1)

        # Both should have same result (flow = 10 mm³/s < 12 mm³/s limit)
        assert check_flow_limit(segment, hotend_fast) is False
        assert check_flow_limit(segment, hotend_slow) is False
