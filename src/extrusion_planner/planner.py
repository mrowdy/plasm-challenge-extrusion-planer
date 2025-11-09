"""End-to-end extrusion planning pipeline.

This module provides the main ExtrusionPlanner class that integrates all components:
- Look-ahead flow prediction
- Preemptive feed rate adjustment
- Pressure lag compensation
- Strict flow limit enforcement

Example:
    >>> from extrusion_planner.planner import ExtrusionPlanner
    >>> from extrusion_planner.models import Segment, HotendConfig, MaterialConfig
    >>>
    >>> segments = [
    ...     Segment(length=12.0, feed_rate=90.0, extrusion=0.48),
    ...     Segment(length=5.0, feed_rate=150.0, extrusion=0.25),
    ... ]
    >>> hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
    >>> material = MaterialConfig(name="TPU Shore 30", shore_hardness=30)
    >>>
    >>> planner = ExtrusionPlanner(lookahead_window=5)
    >>> adjusted = planner.process(segments, hotend, material)
"""

from typing import List

from extrusion_planner.adjuster import apply_preemptive_slowdown, limit_feed_rate
from extrusion_planner.models import HotendConfig, MaterialConfig, Segment
from extrusion_planner.pressure import CompensationStrategy, apply_pressure_compensation


class ExtrusionPlanner:
    """End-to-end extrusion planning system.

    Integrates look-ahead flow prediction, preemptive feed rate adjustment,
    pressure lag compensation, and strict flow limit enforcement.

    The planning pipeline operates in three stages:
    1. Preemptive slowdown: Uses look-ahead to slow down before high-flow regions
    2. Pressure compensation: Slows down after high-flow events for pressure stabilization
    3. Safety limits: Enforces strict volumetric flow limits on all segments

    Args:
        lookahead_window: Number of segments to analyze ahead for flow prediction.
                         Larger windows detect peaks earlier but increase computation.
                         Default: 5 segments (recommended for most use cases)
        compensation_strategy: Strategy for pressure compensation calculation.
                              Default: CompensationStrategy.COMBINED (adapts to both
                              hotend response time and material softness)

    Example:
        >>> planner = ExtrusionPlanner(lookahead_window=5)
        >>> adjusted = planner.process(segments, hotend_config, material_config)
    """

    def __init__(
        self,
        lookahead_window: int = 5,
        compensation_strategy: CompensationStrategy = CompensationStrategy.COMBINED,
    ):
        """Initialize the extrusion planner.

        Args:
            lookahead_window: Number of segments to look ahead (default: 5)
            compensation_strategy: Pressure compensation strategy (default: COMBINED)

        Raises:
            ValueError: If lookahead_window is less than 1
        """
        if lookahead_window < 1:
            raise ValueError(f"lookahead_window must be >= 1, got {lookahead_window}")

        self.lookahead_window = lookahead_window
        self.compensation_strategy = compensation_strategy

    def process(
        self,
        segments: List[Segment],
        hotend_config: HotendConfig,
        material_config: MaterialConfig,
    ) -> List[Segment]:
        """Process segments through the complete extrusion planning pipeline.

        The pipeline applies adjustments in the following order:
        1. Preemptive slowdown: Reduces feed rate before predicted high-flow regions
        2. Pressure compensation: Reduces feed rate after high-flow events to allow
           pressure stabilization (accounts for hotend response time and material softness)
        3. Safety limits: Enforces strict volumetric flow limits on all segments

        Args:
            segments: List of extrusion segments to process
            hotend_config: Hotend equipment configuration (flow capacity, response time)
            material_config: Material properties (Shore hardness)

        Returns:
            List of adjusted segments with modified feed rates. Original segments
            are not modified (immutable design). Only feed_rate is adjusted;
            length and extrusion remain unchanged.

        Example:
            >>> segments = [
            ...     Segment(length=12.0, feed_rate=90.0, extrusion=0.48),
            ...     Segment(length=5.0, feed_rate=150.0, extrusion=0.25),
            ... ]
            >>> hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
            >>> material = MaterialConfig(name="TPU Shore 30", shore_hardness=30)
            >>> planner = ExtrusionPlanner()
            >>> adjusted = planner.process(segments, hotend, material)

        Note:
            - Empty segment lists return []
            - Travel moves (extrusion=0) are never adjusted
            - All adjustments preserve segment length and extrusion amount
            - Feed rates can only be reduced, never increased (safety)
        """
        # Handle empty input
        if not segments:
            return []

        # Stage 1: Apply preemptive slowdown based on look-ahead prediction
        # This slows down before high-flow regions to prevent under-extrusion
        adjusted = apply_preemptive_slowdown(
            segments, window_size=self.lookahead_window, hotend=hotend_config
        )

        # Stage 2: Apply pressure compensation after high-flow events
        # This accounts for pressure lag in the hotend and material softness
        adjusted = apply_pressure_compensation(
            adjusted,
            hotend=hotend_config,
            material=material_config,
            strategy=self.compensation_strategy,
        )

        # Stage 3: Apply strict flow limits as final safety check
        # Ensures no segment exceeds the hotend's volumetric flow capacity
        adjusted = [limit_feed_rate(seg, hotend_config) for seg in adjusted]

        return adjusted

    def __repr__(self) -> str:
        """Return string representation of the planner."""
        return (
            f"ExtrusionPlanner(lookahead_window={self.lookahead_window}, "
            f"compensation_strategy={self.compensation_strategy.name})"
        )
