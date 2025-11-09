"""Volumetric flow rate calculation and limit checking for extrusion planning."""

from extrusion_planner.models.hotend import HotendConfig
from extrusion_planner.models.segment import Segment


def calculate_volumetric_flow(segment: Segment) -> float:
    """Calculate the volumetric flow rate for a segment.

    This is the rate at which material must be extruded through the hotend,
    measured in cubic millimeters per second (mm³/s).

    For travel moves (extrusion=0), the flow rate is 0.

    Args:
        segment: The segment to calculate flow rate for

    Returns:
        Volumetric flow rate in mm³/s

    Examples:
        >>> seg = Segment(length=10.0, feed_rate=60.0, extrusion=0.5)
        >>> calculate_volumetric_flow(seg)
        0.05

        >>> travel = Segment(length=20.0, feed_rate=120.0, extrusion=0.0)
        >>> calculate_volumetric_flow(travel)
        0.0
    """
    return segment.extrusion_rate()


def check_flow_limit(segment: Segment, hotend: HotendConfig) -> bool:
    """Check if a segment's flow rate exceeds the hotend's volumetric flow limit.

    Args:
        segment: The segment to check
        hotend: The hotend configuration with max_volumetric_flow limit

    Returns:
        True if the segment exceeds the hotend's flow limit, False otherwise

    Examples:
        >>> seg = Segment(length=10.0, feed_rate=60.0, extrusion=2.0)
        >>> hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        >>> check_flow_limit(seg, hotend)
        True

        >>> seg = Segment(length=10.0, feed_rate=60.0, extrusion=0.5)
        >>> check_flow_limit(seg, hotend)
        False
    """
    flow = calculate_volumetric_flow(segment)
    return flow > hotend.max_volumetric_flow
