"""End-to-end extrusion planning pipeline."""

from typing import List

from extrusion_planner.adjuster import apply_preemptive_slowdown, limit_feed_rate
from extrusion_planner.models import HotendConfig, MaterialConfig, Segment
from extrusion_planner.pressure import CompensationStrategy, apply_pressure_compensation


class ExtrusionPlanner:
    """Extrusion planning system integrating look-ahead, compensation, and flow limits."""

    def __init__(
        self,
        lookahead_window: int = 5,
        compensation_strategy: CompensationStrategy = CompensationStrategy.COMBINED,
    ):
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
        """Process segments through complete planning pipeline."""
        if not segments:
            return []

        adjusted = apply_preemptive_slowdown(
            segments, window_size=self.lookahead_window, hotend=hotend_config
        )
        adjusted = apply_pressure_compensation(
            adjusted,
            hotend=hotend_config,
            material=material_config,
            strategy=self.compensation_strategy,
        )
        adjusted = [limit_feed_rate(seg, hotend_config) for seg in adjusted]
        return adjusted

    def __repr__(self) -> str:
        return (
            f"ExtrusionPlanner(lookahead_window={self.lookahead_window}, "
            f"compensation_strategy={self.compensation_strategy.name})"
        )
