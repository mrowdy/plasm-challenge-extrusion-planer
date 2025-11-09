"""Tests for core data models.

This module re-exports all test classes for backwards compatibility.
Tests are now organized in separate files: test_segment.py, test_hotend.py, test_material.py

Tests can also be run by importing directly from the models package level:
    from extrusion_planner.models import Segment, HotendConfig, MaterialConfig
"""

from tests.test_hotend import TestHotendConfig
from tests.test_material import TestMaterialConfig
from tests.test_segment import TestSegment

__all__ = [
    "TestSegment",
    "TestHotendConfig",
    "TestMaterialConfig",
]
