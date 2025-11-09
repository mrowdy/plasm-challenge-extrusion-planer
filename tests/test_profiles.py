"""Tests for hotend and material profile presets."""

import pytest

from extrusion_planner.models.hotend import HotendConfig
from extrusion_planner.models.material import MaterialConfig
from extrusion_planner.profiles import (
    HotendProfile,
    MaterialType,
    create_hotend_config,
    create_material_config,
)


class TestHotendProfile:
    """Tests for HotendProfile enum and create_hotend_config factory."""

    def test_standard_profile(self):
        """Test STANDARD hotend profile specifications."""
        hotend = create_hotend_config(HotendProfile.STANDARD)

        assert isinstance(hotend, HotendConfig)
        assert hotend.max_volumetric_flow == 12.0
        assert hotend.response_time == 0.08

    def test_fast_response_profile(self):
        """Test FAST_RESPONSE hotend profile specifications."""
        hotend = create_hotend_config(HotendProfile.FAST_RESPONSE)

        assert isinstance(hotend, HotendConfig)
        assert hotend.max_volumetric_flow == 15.0
        assert hotend.response_time == 0.03

    def test_induction_profile(self):
        """Test INDUCTION hotend profile specifications."""
        hotend = create_hotend_config(HotendProfile.INDUCTION)

        assert isinstance(hotend, HotendConfig)
        assert hotend.max_volumetric_flow == 18.0
        assert hotend.response_time == 0.01

    def test_profiles_ordered_by_performance(self):
        """Test that profiles are ordered from slowest to fastest."""
        standard = create_hotend_config(HotendProfile.STANDARD)
        fast = create_hotend_config(HotendProfile.FAST_RESPONSE)
        induction = create_hotend_config(HotendProfile.INDUCTION)

        # Response times should decrease (faster response)
        assert standard.response_time > fast.response_time > induction.response_time

        # Flow capacities should increase
        assert standard.max_volumetric_flow < fast.max_volumetric_flow
        assert fast.max_volumetric_flow < induction.max_volumetric_flow

    def test_invalid_profile_raises_error(self):
        """Test that invalid profile raises ValueError."""
        with pytest.raises(ValueError, match="Unknown hotend profile"):
            create_hotend_config("invalid_profile")


class TestMaterialType:
    """Tests for MaterialType enum and create_material_config factory."""

    def test_pla_material(self):
        """Test PLA material specifications."""
        material = create_material_config(MaterialType.PLA)

        assert isinstance(material, MaterialConfig)
        assert material.name == "PLA"
        assert material.shore_hardness == 75

    def test_petg_material(self):
        """Test PETG material specifications."""
        material = create_material_config(MaterialType.PETG)

        assert isinstance(material, MaterialConfig)
        assert material.name == "PETG"
        assert material.shore_hardness == 70

    def test_tpu_shore_95_material(self):
        """Test TPU Shore 95 material specifications."""
        material = create_material_config(MaterialType.TPU_SHORE_95)

        assert isinstance(material, MaterialConfig)
        assert material.name == "TPU Shore 95"
        assert material.shore_hardness == 95

    def test_tpu_shore_60_material(self):
        """Test TPU Shore 60 material specifications."""
        material = create_material_config(MaterialType.TPU_SHORE_60)

        assert isinstance(material, MaterialConfig)
        assert material.name == "TPU Shore 60"
        assert material.shore_hardness == 60

    def test_tpu_shore_30_material(self):
        """Test TPU Shore 30 (very soft) material specifications."""
        material = create_material_config(MaterialType.TPU_SHORE_30)

        assert isinstance(material, MaterialConfig)
        assert material.name == "TPU Shore 30"
        assert material.shore_hardness == 30

    def test_materials_ordered_by_hardness(self):
        """Test that materials are ordered correctly by Shore hardness."""
        tpu_95 = create_material_config(MaterialType.TPU_SHORE_95)
        pla = create_material_config(MaterialType.PLA)
        petg = create_material_config(MaterialType.PETG)
        tpu_60 = create_material_config(MaterialType.TPU_SHORE_60)
        tpu_30 = create_material_config(MaterialType.TPU_SHORE_30)

        # Shore hardness should be in descending order
        assert tpu_95.shore_hardness > pla.shore_hardness
        assert pla.shore_hardness > petg.shore_hardness
        assert petg.shore_hardness > tpu_60.shore_hardness
        assert tpu_60.shore_hardness > tpu_30.shore_hardness

    def test_all_shore_values_in_valid_range(self):
        """Test that all material Shore values are valid (0-100)."""
        for material_type in MaterialType:
            material = create_material_config(material_type)
            assert 0 <= material.shore_hardness <= 100

    def test_invalid_material_raises_error(self):
        """Test that invalid material type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown material type"):
            create_material_config("invalid_material")


class TestProfileCombinations:
    """Tests for common hotend + material combinations."""

    def test_standard_hotend_with_soft_tpu(self):
        """Test worst-case scenario: slow hotend with very soft material."""
        hotend = create_hotend_config(HotendProfile.STANDARD)
        material = create_material_config(MaterialType.TPU_SHORE_30)

        # This combination should work but need maximum compensation
        assert hotend.response_time == 0.08  # Slowest
        assert material.shore_hardness == 30  # Softest

    def test_induction_hotend_with_pla(self):
        """Test best-case scenario: fast hotend with rigid material."""
        hotend = create_hotend_config(HotendProfile.INDUCTION)
        material = create_material_config(MaterialType.PLA)

        # This combination should need minimal compensation
        assert hotend.response_time == 0.01  # Fastest
        assert material.shore_hardness == 75  # Rigid

    def test_fast_response_with_medium_tpu(self):
        """Test balanced scenario: fast hotend with medium TPU."""
        hotend = create_hotend_config(HotendProfile.FAST_RESPONSE)
        material = create_material_config(MaterialType.TPU_SHORE_60)

        # This combination should be moderate
        assert hotend.response_time == 0.03
        assert material.shore_hardness == 60

    def test_all_combinations_create_valid_configs(self):
        """Test that all hotend + material combinations are valid."""
        for hotend_profile in HotendProfile:
            for material_type in MaterialType:
                hotend = create_hotend_config(hotend_profile)
                material = create_material_config(material_type)

                # Both should be valid configurations
                assert isinstance(hotend, HotendConfig)
                assert isinstance(material, MaterialConfig)
                assert hotend.response_time > 0
                assert hotend.max_volumetric_flow > 0
                assert 0 <= material.shore_hardness <= 100
