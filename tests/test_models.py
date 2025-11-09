"""Tests for core data models."""

import pytest

from extrusion_planner.models import Segment


class TestSegment:
    """Tests for the Segment model."""

    def test_valid_segment_creation(self):
        """Test creating a valid segment with all positive values."""
        seg = Segment(length=12.0, feed_rate=90.0, extrusion=0.48)
        assert seg.length == 12.0
        assert seg.feed_rate == 90.0
        assert seg.extrusion == 0.48

    def test_travel_move_creation(self):
        """Test creating a travel move (non-printing segment with extrusion=0)."""
        seg = Segment(length=10.0, feed_rate=150.0, extrusion=0.0)
        assert seg.length == 10.0
        assert seg.feed_rate == 150.0
        assert seg.extrusion == 0.0

    def test_negative_length_raises_error(self):
        """Test that negative length raises ValueError."""
        with pytest.raises(ValueError, match="length must be positive"):
            Segment(length=-5.0, feed_rate=90.0, extrusion=0.48)

    def test_zero_length_raises_error(self):
        """Test that zero length raises ValueError."""
        with pytest.raises(ValueError, match="length must be positive"):
            Segment(length=0.0, feed_rate=90.0, extrusion=0.48)

    def test_negative_feed_rate_raises_error(self):
        """Test that negative feed_rate raises ValueError."""
        with pytest.raises(ValueError, match="feed_rate must be positive"):
            Segment(length=12.0, feed_rate=-90.0, extrusion=0.48)

    def test_zero_feed_rate_raises_error(self):
        """Test that zero feed_rate raises ValueError."""
        with pytest.raises(ValueError, match="feed_rate must be positive"):
            Segment(length=12.0, feed_rate=0.0, extrusion=0.48)

    def test_negative_extrusion_raises_error(self):
        """Test that negative extrusion raises ValueError."""
        with pytest.raises(ValueError, match="extrusion must be non-negative"):
            Segment(length=12.0, feed_rate=90.0, extrusion=-0.5)

    def test_travel_time_calculation(self):
        """Test travel_time() returns correct value in seconds.

        For a segment with length=12.0mm and feed_rate=90.0mm/min:
        travel_time = (12.0 / 90.0) * 60 = 8.0 seconds
        """
        seg = Segment(length=12.0, feed_rate=90.0, extrusion=0.48)
        assert seg.travel_time() == pytest.approx(8.0)

    def test_travel_time_high_speed(self):
        """Test travel_time() for high-speed movement.

        For length=5.0mm and feed_rate=150.0mm/min:
        travel_time = (5.0 / 150.0) * 60 = 2.0 seconds
        """
        seg = Segment(length=5.0, feed_rate=150.0, extrusion=0.25)
        assert seg.travel_time() == pytest.approx(2.0)

    def test_extrusion_rate_calculation(self):
        """Test extrusion_rate() returns correct volumetric flow in mm³/s.

        For segment with extrusion=0.48mm³ and travel_time=8.0s:
        extrusion_rate = 0.48 / 8.0 = 0.06 mm³/s
        """
        seg = Segment(length=12.0, feed_rate=90.0, extrusion=0.48)
        assert seg.extrusion_rate() == pytest.approx(0.06)

    def test_extrusion_rate_high_flow(self):
        """Test extrusion_rate() for high flow scenario.

        For segment with extrusion=0.25mm³ and travel_time=2.0s:
        extrusion_rate = 0.25 / 2.0 = 0.125 mm³/s
        """
        seg = Segment(length=5.0, feed_rate=150.0, extrusion=0.25)
        assert seg.extrusion_rate() == pytest.approx(0.125)

    def test_extrusion_rate_for_travel_move(self):
        """Test extrusion_rate() returns 0.0 for travel moves (extrusion=0)."""
        seg = Segment(length=10.0, feed_rate=150.0, extrusion=0.0)
        assert seg.extrusion_rate() == 0.0

    def test_segment_immutability(self):
        """Test that Segment is immutable (frozen dataclass)."""
        seg = Segment(length=12.0, feed_rate=90.0, extrusion=0.48)
        with pytest.raises(Exception):  # FrozenInstanceError in Python 3.11+
            seg.length = 15.0

    def test_realistic_printing_segment(self):
        """Test with realistic 3D printing values.

        Typical extrusion segment:
        - 20mm length
        - 60mm/min feed rate (1mm/s)
        - 0.5mm³ extrusion volume
        - Expected travel time: 20 seconds
        - Expected flow rate: 0.025 mm³/s
        """
        seg = Segment(length=20.0, feed_rate=60.0, extrusion=0.5)
        assert seg.travel_time() == pytest.approx(20.0)
        assert seg.extrusion_rate() == pytest.approx(0.025)

    def test_edge_case_very_small_segment(self):
        """Test with very small but valid segment."""
        seg = Segment(length=0.1, feed_rate=30.0, extrusion=0.001)
        # travel_time = (0.1 / 30.0) * 60 = 0.2 seconds
        assert seg.travel_time() == pytest.approx(0.2)
        # extrusion_rate = 0.001 / 0.2 = 0.005 mm³/s
        assert seg.extrusion_rate() == pytest.approx(0.005)

    def test_edge_case_very_long_segment(self):
        """Test with very long segment."""
        seg = Segment(length=1000.0, feed_rate=120.0, extrusion=50.0)
        # travel_time = (1000.0 / 120.0) * 60 = 500 seconds
        assert seg.travel_time() == pytest.approx(500.0)
        # extrusion_rate = 50.0 / 500.0 = 0.1 mm³/s
        assert seg.extrusion_rate() == pytest.approx(0.1)
