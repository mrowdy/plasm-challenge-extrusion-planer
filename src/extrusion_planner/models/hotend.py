"""Hotend configuration model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HotendConfig:
    """Hotend equipment configuration."""

    max_volumetric_flow: float
    response_time: float

    def __post_init__(self) -> None:
        """Validate hotend configuration."""
        if self.max_volumetric_flow <= 0:
            raise ValueError(
                f"max_volumetric_flow must be positive, got {self.max_volumetric_flow}"
            )
        if self.response_time <= 0:
            raise ValueError(f"response_time must be positive, got {self.response_time}")
