"""Hotend configuration model for extrusion planning."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HotendConfig:
    """Hotend equipment configuration parameters.

    This represents physical hotend characteristics, separate from material properties.

    Attributes:
        max_volumetric_flow: Maximum volumetric flow rate in cubic millimeters per second
        response_time: Hotend thermal response time in seconds
    """

    max_volumetric_flow: float
    response_time: float

    def __post_init__(self) -> None:
        """Validate that all values are positive."""
        if self.max_volumetric_flow <= 0:
            raise ValueError(
                f"max_volumetric_flow must be positive, got {self.max_volumetric_flow}"
            )
        if self.response_time <= 0:
            raise ValueError(f"response_time must be positive, got {self.response_time}")
