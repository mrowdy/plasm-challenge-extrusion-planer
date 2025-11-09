"""Volumetric flow calculation and limit checking."""

from extrusion_planner.models.hotend import HotendConfig
from extrusion_planner.models.segment import Segment


def calculate_volumetric_flow(segment: Segment) -> float:
    """Calculate volumetric flow rate in mm³/s."""
    return segment.extrusion_rate()


def check_flow_limit(segment: Segment, hotend: HotendConfig) -> bool:
    """Check if segment flow exceeds hotend limit."""
    flow = calculate_volumetric_flow(segment)
    return flow > hotend.max_volumetric_flow
