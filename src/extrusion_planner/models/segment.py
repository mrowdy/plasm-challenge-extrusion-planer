"""Segment model for extrusion planning."""

from dataclasses import dataclass

SECONDS_PER_MINUTE = 60.0


@dataclass(frozen=True)
class Segment:
    """Extrusion segment with length, feed_rate, and extrusion volume."""

    length: float
    feed_rate: float
    extrusion: float

    def __post_init__(self) -> None:
        """Validate segment parameters."""
        if self.length <= 0:
            raise ValueError(f"length must be positive, got {self.length}")
        if self.feed_rate <= 0:
            raise ValueError(f"feed_rate must be positive, got {self.feed_rate}")
        if self.extrusion < 0:
            raise ValueError(f"extrusion must be non-negative, got {self.extrusion}")

    def travel_time(self) -> float:
        """Travel time in seconds."""
        return (self.length / self.feed_rate) * SECONDS_PER_MINUTE

    def extrusion_rate(self) -> float:
        """Volumetric extrusion rate in mm³/s."""
        if self.extrusion == 0:
            return 0.0
        return self.extrusion / self.travel_time()
