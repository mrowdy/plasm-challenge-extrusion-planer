"""Hotend and material profile presets."""

from enum import Enum

from extrusion_planner.models.hotend import HotendConfig
from extrusion_planner.models.material import MaterialConfig


class HotendProfile(Enum):
    """Common hotend equipment profiles."""

    STANDARD = "standard"
    FAST_RESPONSE = "fast_response"
    INDUCTION = "induction"


class MaterialType(Enum):
    """Common material types."""

    PLA = "pla"
    PETG = "petg"
    TPU_SHORE_95 = "tpu_shore_95"
    TPU_SHORE_60 = "tpu_shore_60"
    TPU_SHORE_30 = "tpu_shore_30"


def create_hotend_config(profile: HotendProfile) -> HotendConfig:
    """Create HotendConfig from predefined profile."""
    if profile == HotendProfile.STANDARD:
        return HotendConfig(max_volumetric_flow=12.0, response_time=0.08)
    elif profile == HotendProfile.FAST_RESPONSE:
        return HotendConfig(max_volumetric_flow=15.0, response_time=0.03)
    elif profile == HotendProfile.INDUCTION:
        return HotendConfig(max_volumetric_flow=18.0, response_time=0.01)
    else:
        raise ValueError(f"Unknown hotend profile: {profile}")


def create_material_config(material_type: MaterialType) -> MaterialConfig:
    """Create MaterialConfig from predefined material type."""
    if material_type == MaterialType.PLA:
        return MaterialConfig(name="PLA", shore_hardness=75)
    elif material_type == MaterialType.PETG:
        return MaterialConfig(name="PETG", shore_hardness=70)
    elif material_type == MaterialType.TPU_SHORE_95:
        return MaterialConfig(name="TPU Shore 95", shore_hardness=95)
    elif material_type == MaterialType.TPU_SHORE_60:
        return MaterialConfig(name="TPU Shore 60", shore_hardness=60)
    elif material_type == MaterialType.TPU_SHORE_30:
        return MaterialConfig(name="TPU Shore 30", shore_hardness=30)
    else:
        raise ValueError(f"Unknown material type: {material_type}")
