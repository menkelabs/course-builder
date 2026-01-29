# Testing Goals and Guidelines

## Core Testing Principles

1. **GUI Tests Must Run with Live GUI**: GUI integration tests should create and interact with actual matplotlib windows. Do NOT switch to headless mode or exclude GUI tests for CI.

2. **Comprehensive Coverage**: All new functionality must have corresponding tests:
   - Point-based selection (click-to-generate-mask)
   - Mask generation from points
   - Feature assignment (green, fairway, bunker, tee)
   - Green center extraction
   - SVG generation with OPCD palette
   - Inkscape annotations

3. **Real Resource Images**: At least one test must use actual resource images (Pictatinny_B.jpg, Pictatinny_G.jpg) to verify real-world functionality.

4. **No Test Exclusion**: Do not exclude tests for CI convenience. All tests should run in the venv.

5. **GUI Backend**: Use Qt5Agg or TkAgg for GUI tests. The GUI is available in the environment.

## Test Categories

### Unit Tests
- Individual component functionality
- Mock dependencies where appropriate
- Fast execution

### Integration Tests
- Component interactions
- Real resource images
- Full workflow verification

### GUI Integration Tests
- **MUST use live matplotlib windows**
- **MUST display actual images**
- **MUST simulate user interactions (clicks, keyboard)**
- Verify visual feedback
- Test complete workflows

## Current Test Files

- `test_interactive.py` - Interactive selection logic (unit tests)
- `test_point_selector.py` - Point-based selection (NEW)
- `test_gui_integration.py` - Live GUI tests with matplotlib windows
- `test_classify.py` - Classification logic
- `test_features.py` - Feature extraction
- `test_client.py` - Pipeline client
- `test_svg.py` - SVG generation
- `test_export.py` - PNG export
- `test_polygons.py` - Polygon generation
- `test_holes.py` - Hole assignment
- `test_gating.py` - Confidence gating
- `test_config.py` - Configuration

## Running Tests

```bash
# Run all tests (including GUI)
cd phase1a
pytest

# Run only GUI tests
pytest -m gui

# Run excluding slow tests
pytest -m "not slow"
```

## Important Notes

- GUI tests require Qt5Agg or TkAgg backend
- GUI tests will create visible windows during execution
- Tests should verify that images are actually displayed (not black)
- Point-based selection tests should verify SAM mask generation works
- All tests should pass in the venv environment
