"""Material configuration model and property converters for extrusion planning."""

from dataclasses import dataclass


def calculate_pressure_compensation_factor(shore_hardness: float) -> float:
    """Calculate pressure compensation factor from Shore hardness.

    Softer materials (lower Shore hardness) require higher compensation factors
    to account for slower pressure response and material deformation.

    The formula is: 1.0 + (1.0 - shore_hardness/100) * 0.8

    This is just a dummy implementation for now and well be adjusted later

    Args:
        shore_hardness: Shore A hardness value (0-100)
            - 0 = theoretical softest material
            - 30 = very soft TPU
            - 75 = rigid PLA
            - 100 = theoretical hardest material

    Returns:
        Compensation factor ranging from 1.0 (rigid) to 1.8 (softest)
            - Shore 100 → 1.0x (no additional compensation)
            - Shore 75 → 1.2x (slight compensation for PLA)
            - Shore 30 → 1.56x (significant compensation for soft TPU)
            - Shore 0 → 1.8x (maximum compensation)

    Raises:
        ValueError: If shore_hardness is not in the range [0, 100]
    """
    if not 0 <= shore_hardness <= 100:
        raise ValueError(f"shore_hardness must be between 0 and 100, got {shore_hardness}")

    return 1.0 + (1.0 - shore_hardness / 100) * 0.8


@dataclass(frozen=True)
class MaterialConfig:
    """Material physical properties configuration.

    This represents material characteristics, separate from equipment configuration.

    Note:
        Shore hardness is measured on the Shore A scale. Lower values indicate softer
        materials (e.g., Shore 30 is very soft TPU), while higher values indicate
        harder materials (e.g., Shore 75 is rigid PLA).

    Attributes:
        name: Material identifier (e.g., "TPU Shore 30", "PLA")
        shore_hardness: Shore A hardness value from 0 (softest) to 100 (hardest)
    """

    name: str
    shore_hardness: float

    def __post_init__(self) -> None:
        """Validate that shore_hardness is within valid range."""
        if not 0 <= self.shore_hardness <= 100:
            raise ValueError(f"shore_hardness must be between 0 and 100, got {self.shore_hardness}")
