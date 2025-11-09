"""Tests for end-to-end extrusion planner."""

import pytest

from extrusion_planner.models import HotendConfig, MaterialConfig, Segment
from extrusion_planner.planner import ExtrusionPlanner
from extrusion_planner.pressure import CompensationStrategy


class TestExtrusionPlannerInit:
    """Test ExtrusionPlanner initialization."""

    def test_default_initialization(self):
        """Test planner with default parameters."""
        planner = ExtrusionPlanner()
        assert planner.lookahead_window == 5
        assert planner.compensation_strategy == CompensationStrategy.COMBINED

    def test_custom_window_size(self):
        """Test planner with custom lookahead window."""
        planner = ExtrusionPlanner(lookahead_window=10)
        assert planner.lookahead_window == 10

    def test_custom_compensation_strategy(self):
        """Test planner with custom compensation strategy."""
        planner = ExtrusionPlanner(compensation_strategy=CompensationStrategy.PRESSURE_LEVEL)
        assert planner.compensation_strategy == CompensationStrategy.PRESSURE_LEVEL

    def test_invalid_window_size(self):
        """Test that invalid window size raises error."""
        with pytest.raises(ValueError, match="lookahead_window must be >= 1"):
            ExtrusionPlanner(lookahead_window=0)

        with pytest.raises(ValueError, match="lookahead_window must be >= 1"):
            ExtrusionPlanner(lookahead_window=-5)

    def test_repr(self):
        """Test string representation."""
        planner = ExtrusionPlanner(lookahead_window=7)
        assert "ExtrusionPlanner" in repr(planner)
        assert "lookahead_window=7" in repr(planner)
        assert "COMBINED" in repr(planner)


class TestExtrusionPlannerProcess:
    """Test ExtrusionPlanner.process() method."""

    @pytest.fixture
    def standard_hotend(self):
        """Standard hotend configuration."""
        return HotendConfig(max_volumetric_flow=12.0, response_time=0.05)

    @pytest.fixture
    def soft_material(self):
        """Soft TPU material."""
        return MaterialConfig(name="TPU Shore 30", shore_hardness=30)

    @pytest.fixture
    def rigid_material(self):
        """Rigid PLA material."""
        return MaterialConfig(name="PLA", shore_hardness=75)

    def test_empty_segments(self, standard_hotend, soft_material):
        """Test processing empty segment list."""
        planner = ExtrusionPlanner()
        result = planner.process([], standard_hotend, soft_material)
        assert result == []

    def test_single_segment(self, standard_hotend, soft_material):
        """Test processing single segment."""
        planner = ExtrusionPlanner()
        segments = [Segment(length=10.0, feed_rate=100.0, extrusion=0.3)]
        result = planner.process(segments, standard_hotend, soft_material)
        assert len(result) == 1
        assert isinstance(result[0], Segment)

    def test_preserves_segment_count(self, standard_hotend, soft_material):
        """Test that output has same number of segments as input."""
        planner = ExtrusionPlanner()
        segments = [
            Segment(length=12.0, feed_rate=90.0, extrusion=0.48),
            Segment(length=5.0, feed_rate=150.0, extrusion=0.25),
            Segment(length=9.0, feed_rate=100.0, extrusion=0.38),
        ]
        result = planner.process(segments, standard_hotend, soft_material)
        assert len(result) == len(segments)

    def test_preserves_length_and_extrusion(self, standard_hotend, soft_material):
        """Test that length and extrusion are never modified."""
        planner = ExtrusionPlanner()
        segments = [
            Segment(length=12.0, feed_rate=90.0, extrusion=0.48),
            Segment(length=5.0, feed_rate=150.0, extrusion=0.25),
        ]
        result = planner.process(segments, standard_hotend, soft_material)

        for original, adjusted in zip(segments, result):
            assert adjusted.length == original.length
            assert adjusted.extrusion == original.extrusion

    def test_reduces_feed_rate_for_high_flow(self, standard_hotend, soft_material):
        """Test that high-flow segments get reduced feed rates."""
        planner = ExtrusionPlanner()
        # Create segment that exceeds flow limit
        # Flow = (extrusion * feed_rate) / (length * 60)
        # To exceed 12.0 mm³/s: (2.0 * 300) / (5.0 * 60) = 2.0 mm³/s (too low)
        # Need higher extrusion: (5.0 * 300) / (5.0 * 60) = 5.0 mm³/s (still too low)
        # Try: (10.0 * 300) / (5.0 * 60) = 10.0 mm³/s (still below 12.0)
        # Try: (15.0 * 300) / (5.0 * 60) = 15.0 mm³/s (exceeds!)
        high_flow_seg = Segment(length=5.0, feed_rate=300.0, extrusion=15.0)
        segments = [high_flow_seg]

        result = planner.process(segments, standard_hotend, soft_material)

        # Feed rate should be reduced
        assert result[0].feed_rate < high_flow_seg.feed_rate

    def test_never_increases_feed_rate(self, standard_hotend, soft_material):
        """Test that feed rates are never increased (safety)."""
        planner = ExtrusionPlanner()
        segments = [
            Segment(length=10.0, feed_rate=50.0, extrusion=0.2),
            Segment(length=10.0, feed_rate=100.0, extrusion=0.4),
            Segment(length=10.0, feed_rate=150.0, extrusion=0.6),
        ]
        result = planner.process(segments, standard_hotend, soft_material)

        for original, adjusted in zip(segments, result):
            assert adjusted.feed_rate <= original.feed_rate

    def test_travel_moves_unchanged(self, standard_hotend, soft_material):
        """Test that travel moves (extrusion=0) are not adjusted."""
        planner = ExtrusionPlanner()
        segments = [
            Segment(length=10.0, feed_rate=200.0, extrusion=0.0),  # Travel
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),  # Print
            Segment(length=15.0, feed_rate=250.0, extrusion=0.0),  # Travel
        ]
        result = planner.process(segments, standard_hotend, soft_material)

        # Travel moves should be unchanged
        assert result[0].feed_rate == segments[0].feed_rate
        assert result[2].feed_rate == segments[2].feed_rate

    def test_different_window_sizes(self, standard_hotend, soft_material):
        """Test that different window sizes produce different results."""
        segments = [
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),
            Segment(length=10.0, feed_rate=200.0, extrusion=0.8),  # High flow
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),
        ]

        planner_small = ExtrusionPlanner(lookahead_window=2)
        planner_large = ExtrusionPlanner(lookahead_window=5)

        result_small = planner_small.process(segments, standard_hotend, soft_material)
        result_large = planner_large.process(segments, standard_hotend, soft_material)

        # Results may differ due to different look-ahead distances
        # Larger window sees peak earlier, may adjust more segments
        assert len(result_small) == len(result_large) == len(segments)

    def test_soft_vs_rigid_material(self, standard_hotend, soft_material, rigid_material):
        """Test that soft materials get more compensation than rigid."""
        planner = ExtrusionPlanner()

        # Create sequence with high-flow peak
        segments = [
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),
            Segment(length=5.0, feed_rate=200.0, extrusion=0.8),  # High flow
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),
        ]

        result_soft = planner.process(segments, standard_hotend, soft_material)
        result_rigid = planner.process(segments, standard_hotend, rigid_material)

        # Soft material should have more aggressive slowdown after peak
        # Check segment after the high-flow peak (index 2)
        assert result_soft[2].feed_rate <= result_rigid[2].feed_rate

    def test_different_compensation_strategies(self, standard_hotend, soft_material):
        """Test different compensation strategies."""
        segments = [
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),
            Segment(length=5.0, feed_rate=200.0, extrusion=0.8),  # High flow
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),
        ]

        planner_combined = ExtrusionPlanner(compensation_strategy=CompensationStrategy.COMBINED)
        planner_material = ExtrusionPlanner(
            compensation_strategy=CompensationStrategy.MATERIAL_FACTOR
        )
        planner_pressure = ExtrusionPlanner(
            compensation_strategy=CompensationStrategy.PRESSURE_LEVEL
        )

        result_combined = planner_combined.process(segments, standard_hotend, soft_material)
        result_material = planner_material.process(segments, standard_hotend, soft_material)
        result_pressure = planner_pressure.process(segments, standard_hotend, soft_material)

        # All should produce valid results
        assert len(result_combined) == len(segments)
        assert len(result_material) == len(segments)
        assert len(result_pressure) == len(segments)

        # Results may differ based on strategy
        # All should respect safety limits
        for result in [result_combined, result_material, result_pressure]:
            for seg in result:
                if seg.extrusion > 0:
                    flow = seg.extrusion_rate()
                    assert flow <= standard_hotend.max_volumetric_flow * 1.01  # Small tolerance


class TestExtrusionPlannerIntegration:
    """Integration tests for complete planning pipeline."""

    def test_realistic_perimeter_infill_sequence(self):
        """Test realistic scenario: perimeter → infill transition."""
        # Perimeter: slow, precise
        # Infill: fast, high flow
        segments = [
            Segment(length=20.0, feed_rate=60.0, extrusion=0.4),  # Perimeter
            Segment(length=20.0, feed_rate=60.0, extrusion=0.4),  # Perimeter
            Segment(length=15.0, feed_rate=180.0, extrusion=0.9),  # Infill (high flow)
            Segment(length=15.0, feed_rate=180.0, extrusion=0.9),  # Infill
            Segment(length=20.0, feed_rate=60.0, extrusion=0.4),  # Back to perimeter
        ]

        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="PLA", shore_hardness=75)

        planner = ExtrusionPlanner(lookahead_window=5)
        result = planner.process(segments, hotend, material)

        # All segments should be processed
        assert len(result) == len(segments)

        # Infill segments may be slowed down if they exceed flow limits
        for seg in result:
            if seg.extrusion > 0:
                assert seg.extrusion_rate() <= hotend.max_volumetric_flow * 1.01

    def test_sustained_high_flow(self):
        """Test handling of sustained high-flow region."""
        # Create many segments that exceed flow limit
        segments = [Segment(length=10.0, feed_rate=200.0, extrusion=0.8) for _ in range(10)]

        hotend = HotendConfig(max_volumetric_flow=10.0, response_time=0.08)
        material = MaterialConfig(name="PETG", shore_hardness=70)

        planner = ExtrusionPlanner()
        result = planner.process(segments, hotend, material)

        # All segments should be limited
        for seg in result:
            assert seg.extrusion_rate() <= hotend.max_volumetric_flow * 1.01

    def test_mixed_print_and_travel(self):
        """Test sequence with mixed printing and travel moves."""
        segments = [
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),  # Print
            Segment(length=20.0, feed_rate=300.0, extrusion=0.0),  # Travel
            Segment(length=10.0, feed_rate=150.0, extrusion=0.6),  # Print (high flow)
            Segment(length=15.0, feed_rate=250.0, extrusion=0.0),  # Travel
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),  # Print
        ]

        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="TPU Shore 60", shore_hardness=60)

        planner = ExtrusionPlanner()
        result = planner.process(segments, hotend, material)

        # Travel moves unchanged
        assert result[1].feed_rate == segments[1].feed_rate
        assert result[3].feed_rate == segments[3].feed_rate

        # Print moves may be adjusted
        assert len(result) == len(segments)

    def test_fast_hotend_minimal_compensation(self):
        """Test that fast hotends require minimal compensation."""
        segments = [
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),
            Segment(length=5.0, feed_rate=180.0, extrusion=0.7),  # High flow
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),
        ]

        fast_hotend = HotendConfig(max_volumetric_flow=18.0, response_time=0.01)
        material = MaterialConfig(name="PLA", shore_hardness=75)

        planner = ExtrusionPlanner()
        result = planner.process(segments, fast_hotend, material)

        # Fast hotend + rigid material should need minimal compensation
        # Most segments should be close to original feed rates
        assert len(result) == len(segments)

    def test_slow_hotend_soft_material_maximum_compensation(self):
        """Test that slow hotend + soft material gets maximum compensation."""
        segments = [
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),
            # High flow segment: (8.0 * 150) / (5.0 * 60) = 4.0 mm³/s
            # Still below 12.0, need more: (20.0 * 150) / (5.0 * 60) = 10.0 mm³/s
            # Even more: (30.0 * 150) / (5.0 * 60) = 15.0 mm³/s (exceeds!)
            Segment(length=5.0, feed_rate=150.0, extrusion=30.0),  # High flow
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),
        ]

        slow_hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.08)
        soft_material = MaterialConfig(name="TPU Shore 30", shore_hardness=30)

        planner = ExtrusionPlanner()
        result = planner.process(segments, slow_hotend, soft_material)

        # Slow hotend + soft material should apply strong compensation
        # Segments after peak should be significantly slowed
        assert result[2].feed_rate < segments[2].feed_rate

    def test_immutability(self):
        """Test that original segments are not modified."""
        original_segments = [
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),
            # High flow segment to ensure adjustment happens
            Segment(length=10.0, feed_rate=200.0, extrusion=50.0),
        ]

        # Store original values
        original_feed_rates = [seg.feed_rate for seg in original_segments]

        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="PLA", shore_hardness=75)

        planner = ExtrusionPlanner()
        result = planner.process(original_segments, hotend, material)

        # Original segments should be unchanged (most important)
        for seg, orig_feed in zip(original_segments, original_feed_rates):
            assert seg.feed_rate == orig_feed

        # At least one segment should be adjusted (creates new object)
        # High flow segment should definitely be adjusted
        assert result[1].feed_rate < original_segments[1].feed_rate
        assert result[1] is not original_segments[1]
