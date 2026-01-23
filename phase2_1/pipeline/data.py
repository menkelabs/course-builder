"""Data loading for Danish Golf Courses Orthophotos (Kaggle)."""

from pathlib import Path
from typing import Iterator, List, Optional, Tuple

import numpy as np

from ..config import CLASS_IDS, CLASS_NAMES

# Danish dataset: ~1123 orthophotos, 1600×900, classes: bunker, green, fairway, tee, water


def load_danish_dataset(
    dataset_dir: Path,
    split: str = "train",
    tile_size: int = 512,
    limit: Optional[int] = None,
) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
    """
    Load Danish Golf Courses images and masks.
    
    Yields (image, mask) pairs. Images are RGB; masks are H×W int arrays
    with class IDs (0=background, 1=fairway, 2=green, 3=tee, 4=bunker, 5=water).
    
    Args:
        dataset_dir: Root of Kaggle dataset (images/ + masks/ or equivalent).
        split: "train" | "val" | "test".
        tile_size: Crop to square tiles of this size (optional tiling).
        limit: Max number of samples (None = all).
    """
    dataset_dir = Path(dataset_dir)
    if not dataset_dir.exists():
        raise FileNotFoundError(
            f"Dataset not found at {dataset_dir}. "
            "Download from: https://www.kaggle.com/datasets/jacotaco/danish-golf-courses-orthophotos"
        )

    # Placeholder: actual layout depends on Kaggle extract. Common patterns:
    #   images/train/, images/val/ + masks/train/, masks/val/
    #   or train/images/, train/masks/
    img_dir = dataset_dir / "images" / split
    mask_dir = dataset_dir / "masks" / split
    if not img_dir.exists():
        img_dir = dataset_dir / split / "images"
        mask_dir = dataset_dir / split / "masks"

    paths: List[Path] = []
    for ext in ("*.png", "*.jpg", "*.tif"):
        paths.extend(img_dir.glob(ext))
    paths = sorted(paths)[:limit]

    for i, img_path in enumerate(paths):
        # Mask naming often matches image (e.g. x.png -> x_mask.png or masks/x.png)
        mask_path = mask_dir / (img_path.stem + "_mask.png")
        if not mask_path.exists():
            mask_path = mask_dir / img_path.name
        if not mask_path.exists():
            continue

        try:
            from PIL import Image
            img = np.array(Image.open(img_path).convert("RGB"))
            mask = np.array(Image.open(mask_path))
        except Exception:
            continue

        # Ensure mask is int class IDs; some datasets use RGB or 0–255 palettes
        if mask.ndim == 3:
            mask = _rgb_mask_to_class_ids(mask)
        elif mask.max() > len(CLASS_IDS) - 1:
            mask = _palette_to_class_ids(mask)

        if tile_size and (img.shape[0] != tile_size or img.shape[1] != tile_size):
            for timg, tmask in _tile_crop(img, mask, tile_size):
                yield timg, tmask
        else:
            yield img, mask


def _rgb_mask_to_class_ids(mask: np.ndarray) -> np.ndarray:
    """Convert RGB mask to class ID map (dataset-specific)."""
    # Stub: map known colors to CLASS_IDS; default 0
    out = np.zeros(mask.shape[:2], dtype=np.int64)
    # TODO: implement per-dataset color → class mapping
    return out


def _palette_to_class_ids(mask: np.ndarray) -> np.ndarray:
    """Convert palette index mask to 0..5 class IDs."""
    # Clamp to valid range
    return np.clip(mask.astype(np.int64), 0, len(CLASS_IDS) - 1)


def _tile_crop(
    img: np.ndarray,
    mask: np.ndarray,
    size: int,
) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
    """Yield non-overlapping (or overlapping) tiles."""
    h, w = img.shape[:2]
    for y in range(0, max(1, h - size + 1), size):
        for x in range(0, max(1, w - size + 1), size):
            endy, endx = min(y + size, h), min(x + size, w)
            timg = img[y:endy, x:endx]
            tmask = mask[y:endy, x:endx]
            if timg.shape[0] >= size // 2 and timg.shape[1] >= size // 2:
                yield timg, tmask
