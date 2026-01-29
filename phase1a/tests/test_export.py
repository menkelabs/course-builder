"""
Tests for PNG export module.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from phase1a.pipeline.export import PNGExporter, export_svg_to_png


def _cairosvg_available():
    """Check if cairosvg is available."""
    try:
        import cairosvg
        return True
    except ImportError:
        return False


@pytest.fixture
def sample_svg_content():
    """Create sample SVG content for testing."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
  <rect x="10" y="10" width="100" height="100" fill="#228b22"/>
</svg>'''


@pytest.fixture
def sample_svg_file(temp_dir, sample_svg_content):
    """Save sample SVG to a file."""
    svg_path = temp_dir / "test.svg"
    with open(svg_path, "w") as f:
        f.write(sample_svg_content)
    return svg_path


class TestPNGExporter:
    """Tests for PNGExporter class."""
    
    def test_init_default(self):
        exporter = PNGExporter()
        assert exporter.width is None
        assert exporter.height is None
        assert exporter.background_color is None
        assert exporter.dpi == 96
    
    def test_init_custom(self):
        exporter = PNGExporter(
            width=1024,
            height=768,
            background_color="#ffffff",
            dpi=150,
        )
        assert exporter.width == 1024
        assert exporter.height == 768
        assert exporter.background_color == "#ffffff"
        assert exporter.dpi == 150
    
    def test_get_dimensions(self, sample_svg_file):
        exporter = PNGExporter()
        
        width, height = exporter.get_dimensions(sample_svg_file)
        
        assert width == 256
        assert height == 256
    
    @pytest.mark.skipif(
        not _cairosvg_available(),
        reason="cairosvg not installed"
    )
    def test_export(self, sample_svg_file, temp_dir):
        exporter = PNGExporter()
        output_path = temp_dir / "output.png"
        
        exporter.export(sample_svg_file, output_path)
        
        assert output_path.exists()
        
        # Verify it's a valid PNG
        from PIL import Image
        img = Image.open(output_path)
        assert img.format == "PNG"
    
    @pytest.mark.skipif(
        not _cairosvg_available(),
        reason="cairosvg not installed"
    )
    def test_export_with_dimensions(self, sample_svg_file, temp_dir):
        exporter = PNGExporter(width=512, height=512)
        output_path = temp_dir / "output.png"
        
        exporter.export(sample_svg_file, output_path)
        
        from PIL import Image
        img = Image.open(output_path)
        assert img.size == (512, 512)
    
    @pytest.mark.skipif(
        not _cairosvg_available(),
        reason="cairosvg not installed"
    )
    def test_export_from_string(self, sample_svg_content, temp_dir):
        exporter = PNGExporter()
        output_path = temp_dir / "output.png"
        
        exporter.export_from_string(sample_svg_content, output_path)
        
        assert output_path.exists()
    
    def test_export_creates_parent_dirs(self, sample_svg_file, temp_dir):
        """Test that export creates parent directories."""
        exporter = PNGExporter()
        output_path = temp_dir / "subdir" / "nested" / "output.png"
        
        # Just verify parent dirs are created (the actual export may fail without cairosvg)
        try:
            exporter.export(sample_svg_file, output_path)
        except ImportError:
            pass  # cairosvg not available, but parent should still be created
        
        assert output_path.parent.exists()


class TestExportConvenienceFunction:
    """Tests for export_svg_to_png convenience function."""
    
    @pytest.mark.skipif(
        not _cairosvg_available(),
        reason="cairosvg not installed"
    )
    def test_export_svg_to_png(self, sample_svg_file, temp_dir):
        output_path = temp_dir / "output.png"
        
        export_svg_to_png(sample_svg_file, output_path)
        
        assert output_path.exists()
    
    @pytest.mark.skipif(
        not _cairosvg_available(),
        reason="cairosvg not installed"
    )
    def test_export_svg_to_png_with_size(self, sample_svg_file, temp_dir):
        output_path = temp_dir / "output.png"
        
        export_svg_to_png(sample_svg_file, output_path, width=128, height=128)
        
        from PIL import Image
        img = Image.open(output_path)
        assert img.size == (128, 128)


class TestPNGExporterEdgeCases:
    """Edge case tests for PNG export."""
    
    def test_get_dimensions_no_unit(self, temp_dir):
        """Test SVG with dimensions without px unit."""
        svg = '''<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="200">
</svg>'''
        svg_path = temp_dir / "no_unit.svg"
        with open(svg_path, "w") as f:
            f.write(svg)
        
        exporter = PNGExporter()
        width, height = exporter.get_dimensions(svg_path)
        
        assert width == 100
        assert height == 200
    
    def test_get_dimensions_with_px(self, temp_dir):
        """Test SVG with px suffix."""
        svg = '''<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="300px" height="400px">
</svg>'''
        svg_path = temp_dir / "with_px.svg"
        with open(svg_path, "w") as f:
            f.write(svg)
        
        exporter = PNGExporter()
        width, height = exporter.get_dimensions(svg_path)
        
        assert width == 300
        assert height == 400
