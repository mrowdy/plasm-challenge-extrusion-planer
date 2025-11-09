"""Tests for visualization utilities."""

import matplotlib
import pytest

# Use non-interactive backend for testing
matplotlib.use("Agg")

import matplotlib.pyplot as plt

from extrusion_planner.models import HotendConfig, MaterialConfig, Segment
from extrusion_planner.visualize import (
    plot_comparison,
    plot_feed_rate_only,
    plot_flow_only,
)


class TestPlotComparison:
    """Test plot_comparison function."""

    @pytest.fixture
    def segments(self):
        """Sample segments for testing."""
        return [
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),
            Segment(length=5.0, feed_rate=150.0, extrusion=0.5),
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),
        ]

    @pytest.fixture
    def adjusted_segments(self):
        """Adjusted segments (slightly different feed rates)."""
        return [
            Segment(length=10.0, feed_rate=90.0, extrusion=0.3),
            Segment(length=5.0, feed_rate=120.0, extrusion=0.5),
            Segment(length=10.0, feed_rate=85.0, extrusion=0.3),
        ]

    @pytest.fixture
    def hotend(self):
        """Standard hotend config."""
        return HotendConfig(max_volumetric_flow=12.0, response_time=0.05)

    @pytest.fixture
    def material(self):
        """Standard material config."""
        return MaterialConfig(name="PLA", shore_hardness=75)

    def test_plot_comparison_creates_figure(self, segments, adjusted_segments, hotend, material):
        """Test that plot_comparison creates a valid figure."""
        fig = plot_comparison(segments, adjusted_segments, hotend, material, show=False)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_comparison_has_three_subplots(
        self, segments, adjusted_segments, hotend, material
    ):
        """Test that figure has 3 subplots."""
        fig = plot_comparison(segments, adjusted_segments, hotend, material, show=False)
        assert len(fig.axes) == 3
        plt.close(fig)

    def test_plot_comparison_with_custom_title(self, segments, adjusted_segments, hotend, material):
        """Test custom title."""
        custom_title = "My Custom Title"
        fig = plot_comparison(
            segments, adjusted_segments, hotend, material, title=custom_title, show=False
        )
        assert custom_title in fig._suptitle.get_text()
        plt.close(fig)

    def test_plot_comparison_empty_segments_raises_error(self, hotend, material):
        """Test that empty segments raise error."""
        with pytest.raises(ValueError, match="Cannot plot empty segment list"):
            plot_comparison([], [], hotend, material, show=False)

    def test_plot_comparison_mismatched_lengths_raises_error(self, segments, hotend, material):
        """Test that mismatched segment lists raise error."""
        with pytest.raises(ValueError, match="Segment lists must be same length"):
            plot_comparison(segments, segments[:2], hotend, material, show=False)

    def test_plot_comparison_single_segment(self, hotend, material):
        """Test plotting single segment."""
        single_orig = [Segment(length=10.0, feed_rate=100.0, extrusion=0.3)]
        single_adj = [Segment(length=10.0, feed_rate=90.0, extrusion=0.3)]

        fig = plot_comparison(single_orig, single_adj, hotend, material, show=False)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_comparison_with_travel_moves(self, hotend, material):
        """Test plotting segments including travel moves."""
        segments_with_travel = [
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),
            Segment(length=20.0, feed_rate=300.0, extrusion=0.0),  # Travel
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),
        ]

        fig = plot_comparison(
            segments_with_travel, segments_with_travel, hotend, material, show=False
        )
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_comparison_soft_material(self, segments, adjusted_segments, hotend):
        """Test plotting with soft material."""
        soft_material = MaterialConfig(name="TPU Shore 30", shore_hardness=30)
        fig = plot_comparison(segments, adjusted_segments, hotend, soft_material, show=False)
        # Material info should appear in title
        assert "Shore 30" in fig._suptitle.get_text()
        plt.close(fig)


class TestPlotFeedRateOnly:
    """Test plot_feed_rate_only function."""

    def test_plot_feed_rate_only_creates_figure(self):
        """Test basic functionality."""
        orig = [
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),
            Segment(length=10.0, feed_rate=120.0, extrusion=0.4),
        ]
        adj = [
            Segment(length=10.0, feed_rate=90.0, extrusion=0.3),
            Segment(length=10.0, feed_rate=110.0, extrusion=0.4),
        ]

        fig = plot_feed_rate_only(orig, adj, show=False)
        assert isinstance(fig, plt.Figure)
        assert len(fig.axes) == 1
        plt.close(fig)

    def test_plot_feed_rate_only_with_custom_title(self):
        """Test custom title."""
        orig = [Segment(length=10.0, feed_rate=100.0, extrusion=0.3)]
        adj = [Segment(length=10.0, feed_rate=90.0, extrusion=0.3)]

        custom_title = "Custom Feed Rate Plot"
        fig = plot_feed_rate_only(orig, adj, title=custom_title, show=False)
        assert custom_title == fig.axes[0].get_title()
        plt.close(fig)

    def test_plot_feed_rate_only_empty_raises_error(self):
        """Test empty segments raise error."""
        with pytest.raises(ValueError, match="Cannot plot empty segment list"):
            plot_feed_rate_only([], [], show=False)

    def test_plot_feed_rate_only_mismatched_lengths_raises_error(self):
        """Test mismatched lengths raise error."""
        orig = [
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),
            Segment(length=10.0, feed_rate=120.0, extrusion=0.4),
        ]
        adj = [Segment(length=10.0, feed_rate=90.0, extrusion=0.3)]

        with pytest.raises(ValueError, match="Segment lists must be same length"):
            plot_feed_rate_only(orig, adj, show=False)


class TestPlotFlowOnly:
    """Test plot_flow_only function."""

    def test_plot_flow_only_creates_figure(self):
        """Test basic functionality."""
        segments = [
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),
            Segment(length=5.0, feed_rate=150.0, extrusion=0.5),
        ]
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)

        fig = plot_flow_only(segments, hotend, show=False)
        assert isinstance(fig, plt.Figure)
        assert len(fig.axes) == 1
        plt.close(fig)

    def test_plot_flow_only_with_custom_title(self):
        """Test custom title."""
        segments = [Segment(length=10.0, feed_rate=100.0, extrusion=0.3)]
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)

        custom_title = "Custom Flow Plot"
        fig = plot_flow_only(segments, hotend, title=custom_title, show=False)
        assert custom_title == fig.axes[0].get_title()
        plt.close(fig)

    def test_plot_flow_only_empty_raises_error(self):
        """Test empty segments raise error."""
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)

        with pytest.raises(ValueError, match="Cannot plot empty segment list"):
            plot_flow_only([], hotend, show=False)

    def test_plot_flow_only_shows_hotend_limit(self):
        """Test that hotend limit line is plotted."""
        segments = [Segment(length=10.0, feed_rate=100.0, extrusion=0.3)]
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)

        fig = plot_flow_only(segments, hotend, show=False)
        ax = fig.axes[0]

        # Check that there are horizontal lines (hotend limit)
        hlines = [line for line in ax.get_lines() if len(line.get_xdata()) > 1]
        assert len(hlines) >= 1  # At least the hotend limit line
        plt.close(fig)


class TestVisualizationIntegration:
    """Integration tests with real planner output."""

    def test_plot_with_planner_output(self):
        """Test plotting actual planner results."""
        from extrusion_planner.planner import ExtrusionPlanner

        original = [
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),
            Segment(length=5.0, feed_rate=200.0, extrusion=20.0),  # High flow
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),
        ]

        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="PLA", shore_hardness=75)

        planner = ExtrusionPlanner()
        adjusted = planner.process(original, hotend, material)

        # Should be able to plot without errors
        fig = plot_comparison(original, adjusted, hotend, material, show=False)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_all_three_utilities(self):
        """Test all three plotting functions with same data."""
        segments = [
            Segment(length=10.0, feed_rate=100.0, extrusion=0.3),
            Segment(length=10.0, feed_rate=120.0, extrusion=0.4),
        ]
        adjusted = [
            Segment(length=10.0, feed_rate=95.0, extrusion=0.3),
            Segment(length=10.0, feed_rate=115.0, extrusion=0.4),
        ]
        hotend = HotendConfig(max_volumetric_flow=12.0, response_time=0.05)
        material = MaterialConfig(name="PETG", shore_hardness=70)

        # All three should work
        fig1 = plot_comparison(segments, adjusted, hotend, material, show=False)
        fig2 = plot_feed_rate_only(segments, adjusted, show=False)
        fig3 = plot_flow_only(segments, hotend, show=False)

        assert all(isinstance(f, plt.Figure) for f in [fig1, fig2, fig3])

        plt.close(fig1)
        plt.close(fig2)
        plt.close(fig3)
