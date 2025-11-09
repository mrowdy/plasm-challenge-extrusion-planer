"""Material configuration model."""

from dataclasses import dataclass

MAX_ADDITIONAL_COMPENSATION = 0.8


def calculate_pressure_compensation_factor(shore_hardness: float) -> float:
    """Calculate pressure compensation factor from Shore hardness (0-100)."""
    if not 0 <= shore_hardness <= 100:
        raise ValueError(f"shore_hardness must be between 0 and 100, got {shore_hardness}")
    return 1.0 + (1.0 - shore_hardness / 100) * MAX_ADDITIONAL_COMPENSATION


@dataclass(frozen=True)
class MaterialConfig:
    """Material physical properties."""

    name: str
    shore_hardness: float

    def __post_init__(self) -> None:
        if not 0 <= self.shore_hardness <= 100:
            raise ValueError(
                f"shore_hardness must be between 0 and 100, got {self.shore_hardness}"
            )
