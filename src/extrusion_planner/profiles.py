"""Hotend and material profile presets for common configurations."""

from enum import Enum

from extrusion_planner.models.hotend import HotendConfig
from extrusion_planner.models.material import MaterialConfig


class HotendProfile(Enum):
    """Common hotend equipment profiles with typical specifications."""

    STANDARD = "standard"  # Standard hotend: slower response, moderate flow
    FAST_RESPONSE = "fast_response"  # Fast-response hotend: quick thermal response
    INDUCTION = "induction"  # Induction hotend: fastest response, highest flow


class MaterialType(Enum):
    """Common material types with Shore hardness values."""

    PLA = "pla"  # Rigid PLA: Shore ~75
    PETG = "petg"  # Semi-rigid PETG: Shore ~70
    TPU_SHORE_95 = "tpu_shore_95"  # Rigid TPU: Shore 95
    TPU_SHORE_60 = "tpu_shore_60"  # Medium TPU: Shore 60
    TPU_SHORE_30 = "tpu_shore_30"  # Very soft TPU: Shore 30


def create_hotend_config(profile: HotendProfile) -> HotendConfig:
    """
    Create a HotendConfig from a predefined profile.

    Each profile represents typical specifications for a class of hotends:
    - STANDARD: Conventional hotend with moderate thermal response
    - FAST_RESPONSE: High-performance hotend with quick thermal adjustment
    - INDUCTION: Cutting-edge induction heating with fastest response

    Args:
        profile: Hotend profile to use

    Returns:
        HotendConfig with specifications matching the selected profile

    Examples:
        >>> standard = create_hotend_config(HotendProfile.STANDARD)
        >>> print(f"Response: {standard.response_time}s")
        Response: 0.08s

        >>> induction = create_hotend_config(HotendProfile.INDUCTION)
        >>> print(f"Max flow: {induction.max_volumetric_flow} mm³/s")
        Max flow: 18.0 mm³/s
    """
    if profile == HotendProfile.STANDARD:
        return HotendConfig(
            max_volumetric_flow=12.0,  # mm³/s - moderate flow capacity
            response_time=0.08,  # seconds - slower thermal response
        )
    elif profile == HotendProfile.FAST_RESPONSE:
        return HotendConfig(
            max_volumetric_flow=15.0,  # mm³/s - higher flow capacity
            response_time=0.03,  # seconds - fast thermal adjustment
        )
    elif profile == HotendProfile.INDUCTION:
        return HotendConfig(
            max_volumetric_flow=18.0,  # mm³/s - highest flow capacity
            response_time=0.01,  # seconds - near-instantaneous response
        )
    else:
        raise ValueError(f"Unknown hotend profile: {profile}")


def create_material_config(material_type: MaterialType) -> MaterialConfig:
    """
    Create a MaterialConfig from a predefined material type.

    Each material type has a characteristic Shore A hardness value:
    - Higher Shore = harder/more rigid material (e.g., PLA at Shore 75)
    - Lower Shore = softer/more flexible material (e.g., soft TPU at Shore 30)

    Shore hardness affects pressure compensation: softer materials require
    more aggressive compensation due to slower pressure response and greater
    material deformation.

    Args:
        material_type: Material type to use

    Returns:
        MaterialConfig with Shore hardness matching the selected material

    Examples:
        >>> pla = create_material_config(MaterialType.PLA)
        >>> print(f"{pla.name}: Shore {pla.shore_hardness}")
        PLA: Shore 75

        >>> soft_tpu = create_material_config(MaterialType.TPU_SHORE_30)
        >>> print(f"{soft_tpu.name}: Shore {soft_tpu.shore_hardness}")
        TPU Shore 30: Shore 30
    """
    if material_type == MaterialType.PLA:
        return MaterialConfig(
            name="PLA",
            shore_hardness=75,  # Rigid plastic
        )
    elif material_type == MaterialType.PETG:
        return MaterialConfig(
            name="PETG",
            shore_hardness=70,  # Semi-rigid, slightly softer than PLA
        )
    elif material_type == MaterialType.TPU_SHORE_95:
        return MaterialConfig(
            name="TPU Shore 95",
            shore_hardness=95,  # Very rigid TPU, almost rigid plastic
        )
    elif material_type == MaterialType.TPU_SHORE_60:
        return MaterialConfig(
            name="TPU Shore 60",
            shore_hardness=60,  # Medium flexibility TPU
        )
    elif material_type == MaterialType.TPU_SHORE_30:
        return MaterialConfig(
            name="TPU Shore 30",
            shore_hardness=30,  # Very soft and flexible TPU
        )
    else:
        raise ValueError(f"Unknown material type: {material_type}")
