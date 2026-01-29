"""
Pytest fixtures for Phase 1A tests.
"""

import json
import tempfile
from pathlib import Path
from typing import List, Dict

import numpy as np
import pytest
from PIL import Image


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_image() -> np.ndarray:
    """Create a sample RGB image for testing."""
    # Create a 256x256 image with different colored regions
    image = np.zeros((256, 256, 3), dtype=np.uint8)
    
    # Blue region (water-like) - top left
    image[0:64, 0:64] = [0, 100, 200]
    
    # Yellow/tan region (bunker-like) - top right
    image[0:64, 192:256] = [230, 200, 150]
    
    # Dark green region (green-like) - center
    image[96:160, 96:160] = [34, 139, 34]
    
    # Light green region (fairway-like) - bottom
    image[192:256, 64:192] = [144, 238, 144]
    
    # Darker green (rough-like) - remaining areas
    image[image.sum(axis=2) == 0] = [85, 107, 47]
    
    return image


@pytest.fixture
def sample_image_file(temp_dir, sample_image) -> Path:
    """Save sample image to a file."""
    image_path = temp_dir / "satellite.png"
    Image.fromarray(sample_image).save(image_path)
    return image_path


@pytest.fixture
def sample_mask() -> np.ndarray:
    """Create a sample binary mask."""
    mask = np.zeros((256, 256), dtype=bool)
    # Circular mask in center
    y, x = np.ogrid[:256, :256]
    center = (128, 128)
    radius = 32
    mask[(x - center[0])**2 + (y - center[1])**2 <= radius**2] = True
    return mask


@pytest.fixture
def sample_masks() -> List[np.ndarray]:
    """Create multiple sample masks."""
    masks = []
    
    # Mask 1: Small circle (green-like)
    mask1 = np.zeros((256, 256), dtype=bool)
    y, x = np.ogrid[:256, :256]
    mask1[(x - 128)**2 + (y - 128)**2 <= 20**2] = True
    masks.append(mask1)
    
    # Mask 2: Rectangle (fairway-like)
    mask2 = np.zeros((256, 256), dtype=bool)
    mask2[200:240, 80:180] = True
    masks.append(mask2)
    
    # Mask 3: Small region (bunker-like)
    mask3 = np.zeros((256, 256), dtype=bool)
    mask3[10:50, 200:250] = True
    masks.append(mask3)
    
    # Mask 4: Top left (water-like)
    mask4 = np.zeros((256, 256), dtype=bool)
    mask4[10:50, 10:50] = True
    masks.append(mask4)
    
    return masks


@pytest.fixture
def sample_green_centers() -> List[Dict]:
    """Create sample green center coordinates."""
    return [
        {"hole": 1, "x": 128, "y": 128},
        {"hole": 2, "x": 200, "y": 50},
        {"hole": 3, "x": 50, "y": 200},
    ]


@pytest.fixture
def green_centers_file(temp_dir, sample_green_centers) -> Path:
    """Save green centers to a file."""
    path = temp_dir / "green_centers.json"
    with open(path, "w") as f:
        json.dump(sample_green_centers, f)
    return path


@pytest.fixture
def mock_mask_data(sample_masks):
    """Create mock MaskData objects."""
    from phase1a.pipeline.masks import MaskData
    
    mask_data_list = []
    for i, mask in enumerate(sample_masks):
        # Calculate bounding box
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)
        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]
        
        mask_data = MaskData(
            id=f"mask_{i:04d}",
            mask=mask,
            area=int(np.sum(mask)),
            bbox=(int(cmin), int(rmin), int(cmax - cmin), int(rmax - rmin)),
            predicted_iou=0.95,
            stability_score=0.98,
        )
        mask_data_list.append(mask_data)
    
    return mask_data_list


@pytest.fixture
def mock_features(mock_mask_data, sample_image):
    """Create mock MaskFeatures objects."""
    from phase1a.pipeline.features import FeatureExtractor
    
    extractor = FeatureExtractor()
    features = extractor.extract_all(mock_mask_data, sample_image)
    return features


@pytest.fixture
def mock_classifications(mock_features):
    """Create mock Classification objects."""
    from phase1a.pipeline.classify import MaskClassifier
    
    classifier = MaskClassifier()
    return classifier.classify_all(mock_features)


@pytest.fixture
def mock_gated_masks(mock_classifications):
    """Create mock gated masks."""
    from phase1a.pipeline.gating import ConfidenceGate
    
    gate = ConfidenceGate(high_threshold=0.5, low_threshold=0.2)
    accepted, review, discarded = gate.gate_all(mock_classifications)
    return accepted, review, discarded


@pytest.fixture
def mock_polygons(mock_mask_data, mock_gated_masks):
    """Create mock PolygonFeature objects."""
    from phase1a.pipeline.polygons import PolygonGenerator
    
    accepted, _, _ = mock_gated_masks
    generator = PolygonGenerator(min_area=10)
    return generator.generate_all(mock_mask_data, accepted)


@pytest.fixture
def pictatinny_b_image() -> Path:
    """Load Pictatinny_B.jpg resource image."""
    image_path = Path(__file__).parent.parent / "resources" / "Pictatinny_B.jpg"
    if not image_path.exists():
        pytest.skip(f"Resource image not found: {image_path}")
    return image_path


@pytest.fixture
def pictatinny_g_image() -> Path:
    """Load Pictatinny_G.jpg resource image."""
    image_path = Path(__file__).parent.parent / "resources" / "Pictatinny_G.jpg"
    if not image_path.exists():
        pytest.skip(f"Resource image not found: {image_path}")
    return image_path


@pytest.fixture
def pictatinny_images(pictatinny_b_image, pictatinny_g_image) -> List[Path]:
    """Load both Pictatinny resource images (same topography)."""
    return [pictatinny_b_image, pictatinny_g_image]


@pytest.fixture
def pictatinny_b_array(pictatinny_b_image) -> np.ndarray:
    """Load Pictatinny_B.jpg as numpy array."""
    return np.array(Image.open(pictatinny_b_image).convert("RGB"))


@pytest.fixture
def pictatinny_g_array(pictatinny_g_image) -> np.ndarray:
    """Load Pictatinny_G.jpg as numpy array."""
    return np.array(Image.open(pictatinny_g_image).convert("RGB"))


@pytest.fixture
def pictatinny_arrays(pictatinny_b_array, pictatinny_g_array) -> List[np.ndarray]:
    """Load both Pictatinny images as numpy arrays."""
    return [pictatinny_b_array, pictatinny_g_array]
