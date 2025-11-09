"""Material configuration model."""

from dataclasses import dataclass

# Shore 0 (softest) adds 80% compensation; Shore 100 (rigid) adds 0%
MAX_ADDITIONAL_COMPENSATION = 0.8


def calculate_pressure_compensation_factor(shore_hardness: float) -> float:
    """Calculate pressure compensation factor from Shore hardness (0-100).

    Formula: 1.0 + (1 - Shore/100) * 0.8
    Shore 100 (rigid) → 1.0x, Shore 30 (soft TPU) → 1.56x, Shore 0 → 1.8x
    """
    if not 0 <= shore_hardness <= 100:
        raise ValueError(f"shore_hardness must be between 0 and 100, got {shore_hardness}")
    return 1.0 + (1.0 - shore_hardness / 100) * MAX_ADDITIONAL_COMPENSATION


@dataclass(frozen=True)
class MaterialConfig:
    """Material physical properties."""

    name: str
    shore_hardness: float

    def __post_init__(self) -> None:
        """Validate material configuration."""
        if not 0 <= self.shore_hardness <= 100:
            raise ValueError(f"shore_hardness must be between 0 and 100, got {self.shore_hardness}")
