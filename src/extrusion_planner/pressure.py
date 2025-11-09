"""Pressure buildup modeling and compensation."""

import math
from enum import Enum
from typing import List

from extrusion_planner.flow_calculator import calculate_volumetric_flow
from extrusion_planner.models.hotend import HotendConfig
from extrusion_planner.models.material import (
    MaterialConfig,
    calculate_pressure_compensation_factor,
)
from extrusion_planner.models.segment import Segment


class DecayModel(Enum):
    """Pressure decay algorithm."""

    EXPONENTIAL = "exponential"
    LINEAR = "linear"


class CompensationStrategy(Enum):
    """Compensation strength strategy."""

    MATERIAL_FACTOR = "material_factor"
    PRESSURE_LEVEL = "pressure_level"
    COMBINED = "combined"


BASELINE_RESPONSE_TIME = 0.05
PRESSURE_THRESHOLD = 0.8
COMPENSATION_WINDOW_MULTIPLIER = 3


class PressureModel:
    """Model hotend pressure buildup and decay."""

    def __init__(
        self,
        hotend: HotendConfig,
        material: MaterialConfig,
        decay_model: DecayModel = DecayModel.EXPONENTIAL,
    ) -> None:
        self.hotend = hotend
        self.material = material
        self.decay_model = decay_model
        self.current_level = 0.0
        material_factor = calculate_pressure_compensation_factor(material.shore_hardness)
        self.decay_time_constant = hotend.response_time * material_factor

    def update(self, extrusion_rate: float, time_delta: float) -> None:
        """Update pressure level based on extrusion rate and time."""
        if time_delta <= 0:
            return

        if extrusion_rate > 0:
            steady_state = extrusion_rate / self.hotend.max_volumetric_flow
            if self.decay_model == DecayModel.EXPONENTIAL:
                approach_factor = math.exp(-time_delta / self.decay_time_constant)
                self.current_level = (
                    steady_state + (self.current_level - steady_state) * approach_factor
                )
            elif self.decay_model == DecayModel.LINEAR:
                change_rate = (steady_state - self.current_level) / self.decay_time_constant
                self.current_level += change_rate * time_delta
        else:
            if self.decay_model == DecayModel.EXPONENTIAL:
                decay_factor = math.exp(-time_delta / self.decay_time_constant)
                self.current_level *= decay_factor
            elif self.decay_model == DecayModel.LINEAR:
                decay_amount = time_delta / self.decay_time_constant
                self.current_level *= max(0.0, 1.0 - decay_amount)

        self.current_level = max(0.0, min(1.0, self.current_level))

    def get_level(self) -> float:
        """Get current pressure level (0.0 to 1.0)."""
        return self.current_level

    def reset(self) -> None:
        """Reset pressure to zero."""
        self.current_level = 0.0


def apply_pressure_compensation(
    segments: List[Segment],
    hotend: HotendConfig,
    material: MaterialConfig,
    strategy: CompensationStrategy = CompensationStrategy.COMBINED,
    decay_model: DecayModel = DecayModel.EXPONENTIAL,
) -> List[Segment]:
    """Apply feed rate compensation after high-flow regions."""
    if not segments:
        return []

    pressure = PressureModel(hotend, material, decay_model)
    adjusted = []
    material_comp_factor = calculate_pressure_compensation_factor(material.shore_hardness)

    for segment in segments:
        pressure_level = pressure.get_level()

        if pressure_level > PRESSURE_THRESHOLD and segment.extrusion > 0:
            if strategy == CompensationStrategy.MATERIAL_FACTOR:
                slowdown_factor = 1.0 / material_comp_factor
            elif strategy == CompensationStrategy.PRESSURE_LEVEL:
                normalized_pressure = (pressure_level - PRESSURE_THRESHOLD) / (
                    1.0 - PRESSURE_THRESHOLD
                )
                slowdown_factor = 1.0 - (0.5 * normalized_pressure)
            elif strategy == CompensationStrategy.COMBINED:
                hotend_response_factor = hotend.response_time / BASELINE_RESPONSE_TIME
                total_compensation = hotend_response_factor * material_comp_factor
                slowdown_factor = 1.0 / max(1.0, total_compensation)
            else:
                slowdown_factor = 1.0

            adjusted_feed = segment.feed_rate * slowdown_factor
            adjusted_segment = Segment(
                length=segment.length,
                feed_rate=adjusted_feed,
                extrusion=segment.extrusion,
            )
            adjusted.append(adjusted_segment)
        else:
            adjusted.append(segment)

        flow = calculate_volumetric_flow(segment)
        time_delta = segment.travel_time()
        pressure.update(flow, time_delta)

    return adjusted
