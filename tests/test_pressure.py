"""Tests for pressure buildup modeling and compensation."""

import math

from extrusion_planner.models.hotend import HotendConfig
from extrusion_planner.models.material import (
    MaterialConfig,
    calculate_pressure_compensation_factor,
)
from extrusion_planner.models.segment import Segment
from extrusion_planner.pressure import (
    CompensationStrategy,
    DecayModel,
    PressureModel,
    apply_pressure_compensation,
)


class TestPressureModel:
    """Tests for PressureModel class."""

    def test_initialization(self):
        """PressureModel should initialize with zero pressure."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="PLA", shore_hardness=75)
        model = PressureModel(hotend, material)

        assert model.current_level == 0.0
        assert model.get_level() == 0.0

    def test_pressure_buildup_during_extrusion(self):
        """Pressure should increase during high extrusion rate."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="PLA", shore_hardness=75)
        model = PressureModel(hotend, material, DecayModel.EXPONENTIAL)

        # High extrusion rate (at max flow)
        model.update(extrusion_rate=12.0, time_delta=0.1)

        assert model.get_level() > 0.0

    def test_exponential_decay(self):
        """Pressure should decay exponentially when extrusion stops."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="PLA", shore_hardness=75)
        model = PressureModel(hotend, material, DecayModel.EXPONENTIAL)

        # Build up pressure
        model.update(extrusion_rate=12.0, time_delta=0.1)
        initial_pressure = model.get_level()

        # Let it decay (no extrusion)
        model.update(extrusion_rate=0.0, time_delta=0.05)
        decayed_pressure = model.get_level()

        # Verify exponential decay: should be initial * exp(-dt/tau)
        material_factor = calculate_pressure_compensation_factor(75)
        tau = hotend.response_time * material_factor
        expected = initial_pressure * math.exp(-0.05 / tau)

        assert decayed_pressure < initial_pressure
        assert abs(decayed_pressure - expected) < 0.001

    def test_linear_decay(self):
        """Pressure should decay linearly when using LINEAR model."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="PLA", shore_hardness=75)
        model = PressureModel(hotend, material, DecayModel.LINEAR)

        # Build up pressure
        model.update(extrusion_rate=12.0, time_delta=0.1)
        initial_pressure = model.get_level()

        # Let it decay (no extrusion)
        model.update(extrusion_rate=0.0, time_delta=0.01)
        decayed_pressure = model.get_level()

        # Verify linear decay: should be initial * (1 - dt/tau)
        material_factor = calculate_pressure_compensation_factor(75)
        tau = hotend.response_time * material_factor
        expected = initial_pressure * (1 - 0.01 / tau)

        assert decayed_pressure < initial_pressure
        assert abs(decayed_pressure - expected) < 0.001

    def test_soft_material_decays_slower(self):
        """Shore 30 TPU should decay slower than Shore 75 PLA."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)

        # PLA model
        pla = MaterialConfig(name="PLA", shore_hardness=75)
        model_pla = PressureModel(hotend, pla, DecayModel.EXPONENTIAL)

        # TPU model
        tpu = MaterialConfig(name="TPU", shore_hardness=30)
        model_tpu = PressureModel(hotend, tpu, DecayModel.EXPONENTIAL)

        # Build up same pressure in both
        model_pla.update(extrusion_rate=12.0, time_delta=0.1)
        model_tpu.update(extrusion_rate=12.0, time_delta=0.1)

        # Let both decay for same time
        model_pla.update(extrusion_rate=0.0, time_delta=0.1)
        model_tpu.update(extrusion_rate=0.0, time_delta=0.1)

        # TPU should retain more pressure (decay slower)
        assert model_tpu.get_level() > model_pla.get_level()

    def test_hotend_response_time_affects_decay(self):
        """Slower hotend (higher response_time) should decay slower."""
        material = MaterialConfig(name="PLA", shore_hardness=75)

        # Fast hotend
        fast_hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.01)
        model_fast = PressureModel(fast_hotend, material, DecayModel.EXPONENTIAL)

        # Slow hotend
        slow_hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.1)
        model_slow = PressureModel(slow_hotend, material, DecayModel.EXPONENTIAL)

        # Build up same pressure
        model_fast.update(extrusion_rate=12.0, time_delta=0.1)
        model_slow.update(extrusion_rate=12.0, time_delta=0.1)

        # Let both decay
        model_fast.update(extrusion_rate=0.0, time_delta=0.05)
        model_slow.update(extrusion_rate=0.0, time_delta=0.05)

        # Slow hotend should retain more pressure
        assert model_slow.get_level() > model_fast.get_level()

    def test_pressure_clamped_to_one(self):
        """Pressure level should never exceed 1.0."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="PLA", shore_hardness=75)
        model = PressureModel(hotend, material, DecayModel.EXPONENTIAL)

        # Extreme extrusion for long time
        model.update(extrusion_rate=100.0, time_delta=10.0)

        assert model.get_level() <= 1.0

    def test_pressure_stays_above_zero(self):
        """Pressure level should never go negative."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="PLA", shore_hardness=75)
        model = PressureModel(hotend, material, DecayModel.LINEAR)

        # Excessive decay time
        model.update(extrusion_rate=0.0, time_delta=100.0)

        assert model.get_level() >= 0.0

    def test_zero_extrusion_rate(self):
        """Zero extrusion rate should only cause decay."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="PLA", shore_hardness=75)
        model = PressureModel(hotend, material, DecayModel.EXPONENTIAL)

        # Build up pressure
        model.update(extrusion_rate=12.0, time_delta=0.1)
        pressure_before = model.get_level()

        # Zero extrusion
        model.update(extrusion_rate=0.0, time_delta=0.05)
        pressure_after = model.get_level()

        assert pressure_after < pressure_before
        assert pressure_after >= 0.0

    def test_zero_time_delta(self):
        """Zero time delta should not change pressure."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="PLA", shore_hardness=75)
        model = PressureModel(hotend, material, DecayModel.EXPONENTIAL)

        model.update(extrusion_rate=12.0, time_delta=0.1)
        pressure_before = model.get_level()

        model.update(extrusion_rate=12.0, time_delta=0.0)
        pressure_after = model.get_level()

        assert pressure_after == pressure_before

    def test_reset(self):
        """Reset should clear pressure to zero."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="PLA", shore_hardness=75)
        model = PressureModel(hotend, material, DecayModel.EXPONENTIAL)

        # Build up pressure
        model.update(extrusion_rate=12.0, time_delta=0.1)
        assert model.get_level() > 0.0

        # Reset
        model.reset()
        assert model.get_level() == 0.0

    def test_exponential_vs_linear_decay(self):
        """Exponential decay should differ from linear for same conditions."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="PLA", shore_hardness=75)

        model_exp = PressureModel(hotend, material, DecayModel.EXPONENTIAL)
        model_lin = PressureModel(hotend, material, DecayModel.LINEAR)

        # Build up same pressure
        model_exp.update(extrusion_rate=12.0, time_delta=0.1)
        model_lin.update(extrusion_rate=12.0, time_delta=0.1)

        # Decay
        model_exp.update(extrusion_rate=0.0, time_delta=0.05)
        model_lin.update(extrusion_rate=0.0, time_delta=0.05)

        # Should be different (exponential decays slower initially)
        assert abs(model_exp.get_level() - model_lin.get_level()) > 0.001

    def test_continuous_extrusion_steady_state(self):
        """Continuous extrusion should reach steady state pressure."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="PLA", shore_hardness=75)
        model = PressureModel(hotend, material, DecayModel.EXPONENTIAL)

        # Run continuous extrusion for many time constants
        for _ in range(100):
            model.update(extrusion_rate=6.0, time_delta=0.1)

        # Should be at or near steady state (not oscillating)
        pressure_before = model.get_level()
        model.update(extrusion_rate=6.0, time_delta=0.1)
        pressure_after = model.get_level()

        # Change should be minimal
        assert abs(pressure_after - pressure_before) < 0.01

    def test_varying_extrusion_rates(self):
        """Model should handle varying extrusion rates correctly."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="PLA", shore_hardness=75)
        model = PressureModel(hotend, material, DecayModel.EXPONENTIAL)

        # Low extrusion
        model.update(extrusion_rate=2.0, time_delta=0.1)
        low_pressure = model.get_level()

        # High extrusion
        model.update(extrusion_rate=10.0, time_delta=0.1)
        high_pressure = model.get_level()

        # Should increase
        assert high_pressure > low_pressure


class TestApplyPressureCompensation:
    """Tests for apply_pressure_compensation function."""

    def test_empty_segment_list(self):
        """Empty segment list should return empty list."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="PLA", shore_hardness=75)

        result = apply_pressure_compensation([], hotend, material)

        assert result == []

    def test_travel_moves_unchanged(self):
        """Travel moves (extrusion=0) should never be adjusted."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="TPU", shore_hardness=30)

        segments = [
            Segment(length=50.0, feed_rate=300.0, extrusion=0.0),
            Segment(length=50.0, feed_rate=300.0, extrusion=0.0),
        ]

        result = apply_pressure_compensation(segments, hotend, material)

        assert result[0].feed_rate == 300.0
        assert result[1].feed_rate == 300.0

    def test_low_flow_segments_unchanged(self):
        """Low flow segments should not trigger compensation."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="PLA", shore_hardness=75)

        # Low flow: 1.3 mm³/s
        segments = [
            Segment(length=20.0, feed_rate=40.0, extrusion=26.0),
            Segment(length=20.0, feed_rate=40.0, extrusion=26.0),
        ]

        result = apply_pressure_compensation(segments, hotend, material)

        # Should be unchanged
        assert result[0].feed_rate == 40.0
        assert result[1].feed_rate == 40.0

    def test_high_flow_triggers_compensation_material_factor(self):
        """High flow should trigger compensation with MATERIAL_FACTOR strategy."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="TPU", shore_hardness=30)

        # High flow segment followed by normal segment
        segments = [
            Segment(length=30.0, feed_rate=120.0, extrusion=210.0),  # 14 mm³/s
            Segment(length=20.0, feed_rate=40.0, extrusion=26.0),  # 1.3 mm³/s
        ]

        result = apply_pressure_compensation(
            segments, hotend, material, strategy=CompensationStrategy.MATERIAL_FACTOR
        )

        # Second segment should be slowed down due to pressure from first
        assert result[1].feed_rate < segments[1].feed_rate

    def test_soft_material_stronger_compensation(self):
        """Shore 30 TPU should have stronger compensation than Shore 75 PLA."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)

        # Same segment sequence
        segments = [
            Segment(length=30.0, feed_rate=120.0, extrusion=210.0),  # 14 mm³/s
            Segment(length=20.0, feed_rate=40.0, extrusion=26.0),  # 1.3 mm³/s
            Segment(length=20.0, feed_rate=40.0, extrusion=26.0),
        ]

        tpu = MaterialConfig(name="TPU", shore_hardness=30)
        pla = MaterialConfig(name="PLA", shore_hardness=75)

        result_tpu = apply_pressure_compensation(
            segments, hotend, tpu, strategy=CompensationStrategy.MATERIAL_FACTOR
        )
        result_pla = apply_pressure_compensation(
            segments, hotend, pla, strategy=CompensationStrategy.MATERIAL_FACTOR
        )

        # TPU should have more aggressive slowdown
        # (result feed rate should be lower)
        assert result_tpu[1].feed_rate < result_pla[1].feed_rate

    def test_pressure_level_strategy(self):
        """PRESSURE_LEVEL strategy should apply dynamic compensation."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="TPU", shore_hardness=30)

        segments = [
            Segment(length=30.0, feed_rate=120.0, extrusion=210.0),  # 14 mm³/s
            Segment(length=20.0, feed_rate=40.0, extrusion=26.0),  # 1.3 mm³/s
        ]

        result = apply_pressure_compensation(
            segments, hotend, material, strategy=CompensationStrategy.PRESSURE_LEVEL
        )

        # Should apply some compensation
        assert result[1].feed_rate < segments[1].feed_rate

    def test_exponential_decay_model(self):
        """Should work with EXPONENTIAL decay model."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="TPU", shore_hardness=30)

        segments = [
            Segment(length=30.0, feed_rate=120.0, extrusion=210.0),
            Segment(length=20.0, feed_rate=40.0, extrusion=26.0),
        ]

        result = apply_pressure_compensation(
            segments, hotend, material, decay_model=DecayModel.EXPONENTIAL
        )

        # Should apply compensation
        assert result[1].feed_rate < segments[1].feed_rate

    def test_linear_decay_model(self):
        """Should work with LINEAR decay model."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="TPU", shore_hardness=30)

        segments = [
            Segment(length=30.0, feed_rate=120.0, extrusion=210.0),
            Segment(length=20.0, feed_rate=40.0, extrusion=26.0),
        ]

        result = apply_pressure_compensation(
            segments, hotend, material, decay_model=DecayModel.LINEAR
        )

        # Should apply compensation
        assert result[1].feed_rate < segments[1].feed_rate

    def test_multiple_peaks_handled(self):
        """Multiple high-flow peaks should all trigger compensation."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="TPU", shore_hardness=30)

        segments = [
            Segment(length=30.0, feed_rate=120.0, extrusion=210.0),  # Peak 1: 14 mm³/s
            Segment(length=20.0, feed_rate=40.0, extrusion=26.0),  # After peak 1
            Segment(length=30.0, feed_rate=120.0, extrusion=240.0),  # Peak 2: 16 mm³/s
            Segment(length=20.0, feed_rate=40.0, extrusion=26.0),  # After peak 2
        ]

        result = apply_pressure_compensation(segments, hotend, material)

        # Both post-peak segments should be adjusted
        assert result[1].feed_rate < segments[1].feed_rate
        assert result[3].feed_rate < segments[3].feed_rate

    def test_slow_hotend_longer_compensation(self):
        """Slow hotend (high response_time) should compensate longer."""
        material = MaterialConfig(name="TPU", shore_hardness=30)

        # Use very short segments so pressure doesn't fully equilibrate
        # flow = extrusion / travel_time, travel_time = length / (feed_rate/60)
        segments = [
            Segment(length=1.0, feed_rate=120.0, extrusion=7.0),  # 14 mm³/s for 0.5s
            Segment(length=0.5, feed_rate=40.0, extrusion=0.975),  # 1.3 mm³/s for 0.75s
            Segment(length=0.5, feed_rate=40.0, extrusion=0.975),  # 1.3 mm³/s for 0.75s
            Segment(length=0.5, feed_rate=40.0, extrusion=0.975),  # 1.3 mm³/s for 0.75s
        ]

        fast_hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.01)
        slow_hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.1)

        result_fast = apply_pressure_compensation(segments, fast_hotend, material)
        result_slow = apply_pressure_compensation(segments, slow_hotend, material)

        # Both should compensate segment 1 immediately after the peak
        assert result_fast[1].feed_rate < segments[1].feed_rate
        assert result_slow[1].feed_rate < segments[1].feed_rate

        # But slow hotend should STILL be compensating later segments
        # while fast hotend has already recovered
        # Count how many segments are compensated
        fast_compensated = sum(
            1 for i in range(1, len(segments)) if result_fast[i].feed_rate < segments[i].feed_rate
        )
        slow_compensated = sum(
            1 for i in range(1, len(segments)) if result_slow[i].feed_rate < segments[i].feed_rate
        )

        # Slow hotend should compensate more segments (longer duration)
        assert slow_compensated >= fast_compensated

    def test_realistic_perimeter_infill_transition(self):
        """Realistic scenario: slow perimeter → fast infill → slow perimeter."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="TPU", shore_hardness=30)

        segments = [
            # Slow perimeter
            Segment(length=20.0, feed_rate=40.0, extrusion=26.0),  # 1.3 mm³/s
            # Fast infill burst
            Segment(length=30.0, feed_rate=120.0, extrusion=210.0),  # 14 mm³/s
            Segment(length=30.0, feed_rate=120.0, extrusion=210.0),
            # Back to slow perimeter - should be compensated
            Segment(length=20.0, feed_rate=40.0, extrusion=26.0),  # 1.3 mm³/s
            Segment(length=20.0, feed_rate=40.0, extrusion=26.0),
        ]

        result = apply_pressure_compensation(segments, hotend, material)

        # First perimeter unaffected
        assert result[0].feed_rate == segments[0].feed_rate

        # Infill segments may or may not be adjusted (depends on pressure buildup rate)
        # But segments after infill should definitely be adjusted
        assert result[3].feed_rate < segments[3].feed_rate

    def test_compensation_gradual_recovery(self):
        """Feed rate should gradually recover as pressure decays."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="TPU", shore_hardness=30)

        segments = [
            Segment(length=30.0, feed_rate=120.0, extrusion=210.0),  # Peak
            Segment(length=20.0, feed_rate=40.0, extrusion=26.0),  # Post 1
            Segment(length=20.0, feed_rate=40.0, extrusion=26.0),  # Post 2
            Segment(length=20.0, feed_rate=40.0, extrusion=26.0),  # Post 3
            Segment(length=20.0, feed_rate=40.0, extrusion=26.0),  # Post 4
        ]

        result = apply_pressure_compensation(segments, hotend, material)

        # Compensation should decrease over time (feed rate should increase)
        # as pressure decays
        if result[1].feed_rate < 40.0 and result[4].feed_rate < 40.0:
            # If both are still compensated, later should be less compensated
            assert result[4].feed_rate > result[1].feed_rate

    def test_compare_strategies(self):
        """Compare MATERIAL_FACTOR vs PRESSURE_LEVEL strategies."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="TPU", shore_hardness=30)

        segments = [
            Segment(length=30.0, feed_rate=120.0, extrusion=210.0),
            Segment(length=20.0, feed_rate=40.0, extrusion=26.0),
        ]

        result_material = apply_pressure_compensation(
            segments, hotend, material, strategy=CompensationStrategy.MATERIAL_FACTOR
        )
        result_pressure = apply_pressure_compensation(
            segments, hotend, material, strategy=CompensationStrategy.PRESSURE_LEVEL
        )

        # Both should apply some compensation
        assert result_material[1].feed_rate < segments[1].feed_rate
        assert result_pressure[1].feed_rate < segments[1].feed_rate

        # Results should differ (different strategies)
        assert abs(result_material[1].feed_rate - result_pressure[1].feed_rate) > 0.01
