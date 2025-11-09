"""Tests for MaterialConfig model and material property converters."""

import pytest

from extrusion_planner.models.material import (
    MaterialConfig,
    calculate_pressure_compensation_factor,
)


class TestMaterialConfig:
    """Tests for the MaterialConfig model."""

    def test_valid_material_creation(self):
        """Test creating a valid material configuration."""
        material = MaterialConfig(name="TPU Shore 30", shore_hardness=30)
        assert material.name == "TPU Shore 30"
        assert material.shore_hardness == 30

    def test_shore_hardness_below_range_raises_error(self):
        """Test that shore_hardness below 0 raises ValueError."""
        with pytest.raises(ValueError, match="shore_hardness must be between 0 and 100"):
            MaterialConfig(name="Invalid", shore_hardness=-1)

    def test_shore_hardness_above_range_raises_error(self):
        """Test that shore_hardness above 100 raises ValueError."""
        with pytest.raises(ValueError, match="shore_hardness must be between 0 and 100"):
            MaterialConfig(name="Invalid", shore_hardness=101)

    def test_shore_hardness_at_minimum(self):
        """Test shore_hardness at minimum valid value (0)."""
        material = MaterialConfig(name="Theoretical Minimum", shore_hardness=0)
        assert material.shore_hardness == 0

    def test_shore_hardness_at_maximum(self):
        """Test shore_hardness at maximum valid value (100)."""
        material = MaterialConfig(name="Theoretical Maximum", shore_hardness=100)
        assert material.shore_hardness == 100

    def test_material_immutability(self):
        """Test that MaterialConfig is immutable (frozen dataclass)."""
        material = MaterialConfig(name="PLA", shore_hardness=75)
        with pytest.raises(Exception):  # FrozenInstanceError in Python 3.11+
            material.shore_hardness = 50

    def test_pla_material_configuration(self):
        """Test realistic PLA material configuration."""
        material = MaterialConfig(name="PLA", shore_hardness=75)
        assert material.name == "PLA"
        assert material.shore_hardness == 75

    def test_petg_material_configuration(self):
        """Test realistic PETG material configuration."""
        material = MaterialConfig(name="PETG", shore_hardness=70)
        assert material.name == "PETG"
        assert material.shore_hardness == 70

    def test_tpu_shore_95_configuration(self):
        """Test realistic TPU Shore 95 configuration."""
        material = MaterialConfig(name="TPU Shore 95", shore_hardness=95)
        assert material.name == "TPU Shore 95"
        assert material.shore_hardness == 95

    def test_tpu_shore_60_configuration(self):
        """Test realistic TPU Shore 60 configuration."""
        material = MaterialConfig(name="TPU Shore 60", shore_hardness=60)
        assert material.name == "TPU Shore 60"
        assert material.shore_hardness == 60

    def test_tpu_shore_30_configuration(self):
        """Test realistic soft TPU Shore 30 configuration."""
        material = MaterialConfig(name="TPU Shore 30", shore_hardness=30)
        assert material.name == "TPU Shore 30"
        assert material.shore_hardness == 30


class TestCalculatePressureCompensationFactor:
    """Tests for calculate_pressure_compensation_factor function."""

    def test_shore_100_rigid_material(self):
        """Test that Shore 100 (rigid) returns 1.0x compensation (no additional)."""
        factor = calculate_pressure_compensation_factor(100)
        assert factor == pytest.approx(1.0)

    def test_shore_75_pla_material(self):
        """Test that Shore 75 (PLA) returns 1.2x compensation."""
        factor = calculate_pressure_compensation_factor(75)
        assert factor == pytest.approx(1.2)

    def test_shore_30_soft_tpu(self):
        """Test that Shore 30 (soft TPU) returns 1.56x compensation."""
        factor = calculate_pressure_compensation_factor(30)
        assert factor == pytest.approx(1.56)

    def test_shore_0_theoretical_softest(self):
        """Test that Shore 0 (theoretical softest) returns 1.8x compensation."""
        factor = calculate_pressure_compensation_factor(0)
        assert factor == pytest.approx(1.8)

    def test_shore_50_mid_range(self):
        """Test mid-range Shore 50 material.

        Formula: 1.0 + (1.0 - 50/100) * 0.8 = 1.0 + 0.5 * 0.8 = 1.4
        """
        factor = calculate_pressure_compensation_factor(50)
        assert factor == pytest.approx(1.4)

    def test_shore_95_tpu_hard(self):
        """Test Shore 95 (hard TPU) returns low compensation.

        Formula: 1.0 + (1.0 - 95/100) * 0.8 = 1.0 + 0.05 * 0.8 = 1.04
        """
        factor = calculate_pressure_compensation_factor(95)
        assert factor == pytest.approx(1.04)

    def test_shore_60_tpu_medium(self):
        """Test Shore 60 (medium TPU).

        Formula: 1.0 + (1.0 - 60/100) * 0.8 = 1.0 + 0.4 * 0.8 = 1.32
        """
        factor = calculate_pressure_compensation_factor(60)
        assert factor == pytest.approx(1.32)

    def test_shore_70_petg(self):
        """Test Shore 70 (PETG).

        Formula: 1.0 + (1.0 - 70/100) * 0.8 = 1.0 + 0.3 * 0.8 = 1.24
        """
        factor = calculate_pressure_compensation_factor(70)
        assert factor == pytest.approx(1.24)

    def test_negative_shore_raises_error(self):
        """Test that negative shore_hardness raises ValueError."""
        with pytest.raises(ValueError, match="shore_hardness must be between 0 and 100"):
            calculate_pressure_compensation_factor(-1)

    def test_above_100_shore_raises_error(self):
        """Test that shore_hardness above 100 raises ValueError."""
        with pytest.raises(ValueError, match="shore_hardness must be between 0 and 100"):
            calculate_pressure_compensation_factor(101)

    def test_compensation_increases_as_hardness_decreases(self):
        """Test that compensation factor increases as material gets softer."""
        factor_100 = calculate_pressure_compensation_factor(100)
        factor_75 = calculate_pressure_compensation_factor(75)
        factor_50 = calculate_pressure_compensation_factor(50)
        factor_30 = calculate_pressure_compensation_factor(30)
        factor_0 = calculate_pressure_compensation_factor(0)

        # Verify strictly increasing compensation as hardness decreases
        assert factor_100 < factor_75 < factor_50 < factor_30 < factor_0

    def test_compensation_range_bounds(self):
        """Test that compensation factor is always within expected range [1.0, 1.8]."""
        # Test various values across the range
        for shore in [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
            factor = calculate_pressure_compensation_factor(shore)
            assert 1.0 <= factor <= 1.8

    def test_linear_relationship(self):
        """Test that the relationship between shore and compensation is linear."""
        # The formula is linear, so the difference should be constant
        factor_0 = calculate_pressure_compensation_factor(0)
        factor_25 = calculate_pressure_compensation_factor(25)
        factor_50 = calculate_pressure_compensation_factor(50)
        factor_75 = calculate_pressure_compensation_factor(75)
        factor_100 = calculate_pressure_compensation_factor(100)

        # Check that increments are equal (linear relationship)
        increment_1 = factor_0 - factor_25
        increment_2 = factor_25 - factor_50
        increment_3 = factor_50 - factor_75
        increment_4 = factor_75 - factor_100

        assert increment_1 == pytest.approx(increment_2)
        assert increment_2 == pytest.approx(increment_3)
        assert increment_3 == pytest.approx(increment_4)
