# Extrusion Planner

Prevents under-extrusion during high-speed 3D printing by analyzing upcoming segments and adjusting feed rates before flow peaks occur. Especially critical for soft materials (TPU) and hotends with slower response times.

## How It Works

- **Look-ahead analysis**: Predicts volumetric flow peaks 3-5 segments ahead
- **Preemptive slowdown**: Reduces feed rate before high-flow regions to prevent pressure buildup
- **Pressure compensation**: Continues adjusting after peaks based on material softness and hotend response time
- **Safety limits**: Hard cap ensures no segment exceeds hotend capacity


## Key Features

- **Separate hotend and material configs** - Same hotend can be used with different materials and vice versa
- **Profile presets** - Quick start with STANDARD/FAST_RESPONSE/INDUCTION hotends and PLA/PETG/TPU materials
- **Immutable design** - Original segments never modified, enabling clear before/after comparison
- **Three compensation strategies** - COMBINED (default), MATERIAL_FACTOR, or PRESSURE_LEVEL

## Setup

```bash
uv sync
```

## Usage

```python
from extrusion_planner import ExtrusionPlanner, HotendConfig, MaterialConfig, Segment

# Define your printing segments (length in mm, feed_rate in mm/min, extrusion in mm³)
segments = [
    Segment(length=15.0, feed_rate=60.0, extrusion=0.3),   # Slow perimeter
    Segment(length=10.0, feed_rate=180.0, extrusion=50.0), # Fast infill (high flow!)
    Segment(length=15.0, feed_rate=60.0, extrusion=0.3),   # Back to perimeter
]

# Configure your hotend
hotend = HotendConfig(
    max_volumetric_flow=12.0,  # mm³/s 
    response_time=0.05,        # seconds (typical: 0.01-0.08)
)

# Configure your material
material = MaterialConfig(
    name="TPU Shore 30",
    shore_hardness=30, 
)

# Process segments
planner = ExtrusionPlanner(lookahead_window=5)
adjusted_segments = planner.process(segments, hotend, material)

# Use adjusted segments
for seg in adjusted_segments:
    print(f"Feed: {seg.feed_rate:.1f} mm/min, Flow: {seg.extrusion_rate():.2f} mm³/s")
```

**See `examples/` for complete working examples with visualization.**

## Development

```bash
uv run pytest tests/ -v  # Run tests
uv run ruff check .      # Lint
uv run ruff format .     # Format
```

