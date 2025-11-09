"""Core data models for extrusion planning."""

from dataclasses import dataclass

# Time conversion constant
SECONDS_PER_MINUTE = 60.0


@dataclass(frozen=True)
class Segment:
    """Represents a single extrusion segment in a print path.

    Note:
        For travel moves (non-printing movements), set extrusion=0.

    Attributes:
        length: Segment length in millimeters
        feed_rate: Movement speed in millimeters per minute
        extrusion: Total extrusion volume for this segment in cubic millimeters.
            Set to 0 for travel moves (non-printing movements).
    """

    length: float
    feed_rate: float
    extrusion: float

    def __post_init__(self) -> None:
        """Validate that all values are positive."""
        if self.length <= 0:
            raise ValueError(f"length must be positive, got {self.length}")
        if self.feed_rate <= 0:
            raise ValueError(f"feed_rate must be positive, got {self.feed_rate}")
        if self.extrusion < 0:
            raise ValueError(f"extrusion must be non-negative, got {self.extrusion}")

    def travel_time(self) -> float:
        """Calculate the time to travel this segment in seconds.

        Returns:
            Travel time in seconds
        """
        return (self.length / self.feed_rate) * SECONDS_PER_MINUTE

    def extrusion_rate(self) -> float:
        """Calculate the volumetric extrusion rate in cubic millimeters per second.

        Returns:
            Extrusion rate in mm³/s. Returns 0.0 for travel moves (extrusion=0).
        """
        if self.extrusion == 0:
            return 0.0
        return self.extrusion / self.travel_time()
