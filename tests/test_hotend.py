"""Tests for HotendConfig model."""

import pytest

from extrusion_planner.models.hotend import HotendConfig


class TestHotendConfig:
    """Tests for the HotendConfig model."""

    def test_valid_hotend_creation(self):
        """Test creating a valid hotend configuration."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        assert hotend.max_volumetric_flow == 12.0
        assert hotend.response_time == 0.05

    def test_negative_max_volumetric_flow_raises_error(self):
        """Test that negative max_volumetric_flow raises ValueError."""
        with pytest.raises(ValueError, match="max_volumetric_flow must be positive"):
            HotendConfig(max_volumetric_flow=-12.0, response_time=0.05)

    def test_zero_max_volumetric_flow_raises_error(self):
        """Test that zero max_volumetric_flow raises ValueError."""
        with pytest.raises(ValueError, match="max_volumetric_flow must be positive"):
            HotendConfig(max_volumetric_flow=0.0, response_time=0.05)

    def test_negative_response_time_raises_error(self):
        """Test that negative response_time raises ValueError."""
        with pytest.raises(ValueError, match="response_time must be positive"):
            HotendConfig(max_volumetric_flow=12.0, response_time=-0.05)

    def test_zero_response_time_raises_error(self):
        """Test that zero response_time raises ValueError."""
        with pytest.raises(ValueError, match="response_time must be positive"):
            HotendConfig(max_volumetric_flow=12.0, response_time=0.0)

    def test_hotend_immutability(self):
        """Test that HotendConfig is immutable (frozen dataclass)."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        with pytest.raises(Exception):  # FrozenInstanceError in Python 3.11+
            hotend.max_volumetric_flow = 15.0

    def test_standard_hotend_configuration(self):
        """Test realistic standard hotend configuration."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.08)
        assert hotend.max_volumetric_flow == 12.0
        assert hotend.response_time == 0.08

    def test_fast_response_hotend_configuration(self):
        """Test realistic fast-response hotend configuration."""
        hotend = HotendConfig(max_volumetric_flow=15.0, response_time=0.03)
        assert hotend.max_volumetric_flow == 15.0
        assert hotend.response_time == 0.03

    def test_induction_hotend_configuration(self):
        """Test realistic induction hotend configuration."""
        hotend = HotendConfig(max_volumetric_flow=18.0, response_time=0.01)
        assert hotend.max_volumetric_flow == 18.0
        assert hotend.response_time == 0.01
