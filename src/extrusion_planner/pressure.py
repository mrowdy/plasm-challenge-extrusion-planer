"""Pressure buildup modeling and compensation for extrusion planning."""

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
    """Algorithm for modeling pressure decay over time."""

    EXPONENTIAL = "exponential"  # Physically accurate: pressure *= exp(-dt/tau)
    LINEAR = "linear"  # Simpler approximation: pressure *= (1 - dt/tau)


class CompensationStrategy(Enum):
    """Strategy for determining compensation strength after high-flow peaks."""

    MATERIAL_FACTOR = "material_factor"  # Use Shore hardness compensation factor
    PRESSURE_LEVEL = "pressure_level"  # Use dynamic pressure level (0.0-1.0)
    COMBINED = "combined"  # Combine hotend response time and material factors


# Baseline response time for normalizing hotend responsiveness (seconds)
# This represents a reference standard hotend for comparison
BASELINE_RESPONSE_TIME = 0.05

# Pressure threshold above which compensation is applied
PRESSURE_THRESHOLD = 0.8

# How many response_time periods to apply compensation after peak
COMPENSATION_WINDOW_MULTIPLIER = 3


class PressureModel:
    """
    Model hotend pressure buildup and decay over time.

    Tracks pressure state as extrusion occurs, accounting for hotend response
    time and material properties. Supports multiple decay models for flexibility.

    Attributes:
        current_level: Pressure level from 0.0 (no pressure) to 1.0 (max pressure)
    """

    def __init__(
        self,
        hotend: HotendConfig,
        material: MaterialConfig,
        decay_model: DecayModel = DecayModel.EXPONENTIAL,
    ) -> None:
        """
        Initialize pressure model.

        Args:
            hotend: Hotend configuration with max_volumetric_flow and response_time
            material: Material configuration with shore_hardness
            decay_model: Algorithm to use for pressure decay (default: exponential)
        """
        self.hotend = hotend
        self.material = material
        self.decay_model = decay_model
        self.current_level = 0.0

        # Calculate material-adjusted decay time constant
        # Softer materials (low Shore) have slower decay
        material_factor = calculate_pressure_compensation_factor(material.shore_hardness)
        self.decay_time_constant = hotend.response_time * material_factor

    def update(self, extrusion_rate: float, time_delta: float) -> None:
        """
        Update pressure level based on extrusion rate and time elapsed.

        Pressure increases with extrusion rate and decreases over time based
        on the selected decay model.

        Args:
            extrusion_rate: Volumetric flow rate in mm³/s
            time_delta: Time elapsed in seconds
        """
        if time_delta <= 0:
            return

        if extrusion_rate > 0:
            # During extrusion: pressure builds up toward steady state
            # Steady state pressure = (extrusion_rate / max_flow)
            # Use exponential approach: P = Pss + (P0 - Pss) * exp(-t/tau)
            steady_state = extrusion_rate / self.hotend.max_volumetric_flow

            if self.decay_model == DecayModel.EXPONENTIAL:
                # Exponential approach to steady state
                approach_factor = math.exp(-time_delta / self.decay_time_constant)
                self.current_level = (
                    steady_state + (self.current_level - steady_state) * approach_factor
                )
            elif self.decay_model == DecayModel.LINEAR:
                # Linear approach to steady state
                change_rate = (steady_state - self.current_level) / self.decay_time_constant
                self.current_level += change_rate * time_delta
        else:
            # No extrusion: pressure decays toward zero
            if self.decay_model == DecayModel.EXPONENTIAL:
                # Exponential decay: P(t) = P0 * exp(-t/tau)
                decay_factor = math.exp(-time_delta / self.decay_time_constant)
                self.current_level *= decay_factor
            elif self.decay_model == DecayModel.LINEAR:
                # Linear decay toward zero
                decay_amount = time_delta / self.decay_time_constant
                self.current_level *= max(0.0, 1.0 - decay_amount)

        # Clamp to valid range
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
    """
    Apply feed rate compensation after high-flow regions to account for pressure lag.

    When hotend pressure builds up during high-flow extrusion, it takes time to
    dissipate. This function reduces feed rates after peaks based on pressure state.

    Args:
        segments: List of segments to process
        hotend: Hotend configuration with max_volumetric_flow and response_time
        material: Material configuration with shore_hardness
        strategy: Compensation strategy to use (default: material factor)
        decay_model: Pressure decay model to use (default: exponential)

    Returns:
        List of segments with adjusted feed rates after high-flow events.
        Travel moves (extrusion=0) are never adjusted.

    Algorithm:
        1. Simulate pressure buildup/decay through all segments
        2. When pressure exceeds threshold, apply compensation to feed rate
        3. Compensation strength determined by selected strategy:
           - MATERIAL_FACTOR: Fixed based on Shore hardness
           - PRESSURE_LEVEL: Dynamic based on current pressure level
           - COMBINED: Scales with both hotend response time and material softness
        4. Creates smooth transitions as pressure decays
    """
    if not segments:
        return []

    # Initialize pressure model
    pressure = PressureModel(hotend, material, decay_model)
    adjusted = []

    # Get material compensation factor for MATERIAL_FACTOR strategy
    material_comp_factor = calculate_pressure_compensation_factor(material.shore_hardness)

    for segment in segments:
        # Check current pressure level BEFORE updating with this segment
        # This way, segments after high-flow peaks see the elevated pressure
        pressure_level = pressure.get_level()

        if pressure_level > PRESSURE_THRESHOLD and segment.extrusion > 0:
            # Apply compensation based on strategy
            if strategy == CompensationStrategy.MATERIAL_FACTOR:
                # Use material factor: softer materials need more slowdown
                # Factor of 1.56 means we slow down TO 1/1.56 = 0.64x speed
                slowdown_factor = 1.0 / material_comp_factor
            elif strategy == CompensationStrategy.PRESSURE_LEVEL:
                # Use pressure level: higher pressure = more slowdown
                # Map pressure [0.8, 1.0] to slowdown [1.0, 0.5]
                # Linear interpolation: at 0.8 → 1.0x, at 1.0 → 0.5x
                normalized_pressure = (pressure_level - PRESSURE_THRESHOLD) / (
                    1.0 - PRESSURE_THRESHOLD
                )
                slowdown_factor = 1.0 - (0.5 * normalized_pressure)
            elif strategy == CompensationStrategy.COMBINED:
                # Combine hotend response time and material factors
                # Formula: total_compensation = (response_time / baseline) * material_factor
                # - Slower hotends (high response_time) → more compensation
                # - Softer materials (low Shore, high material_factor) → more compensation
                # - Fast hotends (low response_time) → less compensation
                hotend_response_factor = hotend.response_time / BASELINE_RESPONSE_TIME
                total_compensation = hotend_response_factor * material_comp_factor

                # Convert to slowdown factor
                # Use max(1.0, ...) to prevent speeding up for very fast hotends
                # Examples:
                # - total_compensation = 2.50 → slowdown = 0.40 (slow to 40% speed)
                # - total_compensation = 0.31 → slowdown = 1.0 (no slowdown)
                # - total_compensation = 1.56 → slowdown = 0.64 (slow to 64% speed)
                slowdown_factor = 1.0 / max(1.0, total_compensation)
            else:
                slowdown_factor = 1.0

            # Apply slowdown
            adjusted_feed = segment.feed_rate * slowdown_factor
            adjusted_segment = Segment(
                length=segment.length,
                feed_rate=adjusted_feed,
                extrusion=segment.extrusion,
            )
            adjusted.append(adjusted_segment)
        else:
            # No compensation needed
            adjusted.append(segment)

        # Update pressure model with this segment's flow
        flow = calculate_volumetric_flow(segment)
        time_delta = segment.travel_time()
        pressure.update(flow, time_delta)

    return adjusted
