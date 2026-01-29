"""
PNG Export Module

Renders SVG to PNG overlay image.
"""

from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class PNGExporter:
    """
    Export SVG to PNG overlay.
    
    Resolution matches satellite image or defined scale.
    """
    
    def __init__(
        self,
        width: Optional[int] = None,
        height: Optional[int] = None,
        background_color: Optional[str] = None,
        dpi: int = 96,
    ):
        """
        Initialize the PNG exporter.
        
        Args:
            width: Output width (None = use SVG dimensions)
            height: Output height (None = use SVG dimensions)
            background_color: Background color (None = transparent)
            dpi: Resolution in DPI
        """
        self.width = width
        self.height = height
        self.background_color = background_color
        self.dpi = dpi
    
    def export(
        self,
        svg_path: Path,
        output_path: Path,
    ) -> None:
        """
        Export SVG to PNG.
        
        Args:
            svg_path: Path to input SVG
            output_path: Path to output PNG
        """
        svg_path = Path(svg_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            import cairosvg
        except ImportError:
            logger.error(
                "cairosvg is required for PNG export. "
                "Install with: pip install cairosvg"
            )
            raise
        
        # Build export options
        kwargs = {
            "url": str(svg_path),
            "write_to": str(output_path),
            "dpi": self.dpi,
        }
        
        if self.width is not None:
            kwargs["output_width"] = self.width
        
        if self.height is not None:
            kwargs["output_height"] = self.height
        
        if self.background_color is not None:
            kwargs["background_color"] = self.background_color
        
        # Export
        cairosvg.svg2png(**kwargs)
        
        logger.info(f"Exported PNG to {output_path}")
    
    def export_from_string(
        self,
        svg_content: str,
        output_path: Path,
    ) -> None:
        """
        Export SVG content string to PNG.
        
        Args:
            svg_content: SVG content as string
            output_path: Path to output PNG
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            import cairosvg
        except ImportError:
            logger.error(
                "cairosvg is required for PNG export. "
                "Install with: pip install cairosvg"
            )
            raise
        
        # Build export options
        kwargs = {
            "bytestring": svg_content.encode("utf-8"),
            "write_to": str(output_path),
            "dpi": self.dpi,
        }
        
        if self.width is not None:
            kwargs["output_width"] = self.width
        
        if self.height is not None:
            kwargs["output_height"] = self.height
        
        if self.background_color is not None:
            kwargs["background_color"] = self.background_color
        
        # Export
        cairosvg.svg2png(**kwargs)
        
        logger.info(f"Exported PNG to {output_path}")
    
    def get_dimensions(self, svg_path: Path) -> Tuple[int, int]:
        """
        Get dimensions from SVG file.
        
        Args:
            svg_path: Path to SVG file
            
        Returns:
            Tuple of (width, height)
        """
        import xml.etree.ElementTree as ET
        
        tree = ET.parse(svg_path)
        root = tree.getroot()
        
        width = root.get("width", "0")
        height = root.get("height", "0")
        
        # Strip units if present
        width = int(float(width.rstrip("px")))
        height = int(float(height.rstrip("px")))
        
        return width, height


def export_svg_to_png(
    svg_path: Path,
    output_path: Path,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> None:
    """
    Convenience function to export SVG to PNG.
    
    Args:
        svg_path: Path to input SVG
        output_path: Path to output PNG
        width: Output width (None = use SVG dimensions)
        height: Output height (None = use SVG dimensions)
    """
    exporter = PNGExporter(width=width, height=height)
    exporter.export(svg_path, output_path)
