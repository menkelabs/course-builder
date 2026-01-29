"""Danish Golf Courses dataset loader from archive.zip."""

import zipfile
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

import numpy as np
from PIL import Image

from ..config import CLASS_IDS

# RGB palette in archive "2. segmentation masks" (6 classes)
# Order: background, fairway, green, tee, bunker, water
DANISH_PALETTE: List[Tuple[int, int, int]] = [
    (0, 0, 0),        # 0 background
    (77, 156, 77),    # 1 fairway
    (142, 243, 122),  # 2 green
    (250, 36, 0),     # 3 tee
    (246, 246, 158),  # 4 bunker
    (46, 200, 231),   # 5 water
]

ORTHO_DIR = "1. orthophotos"
MASK_DIR = "2. segmentation masks"


def _rgb_to_class_id(mask_rgb: np.ndarray) -> np.ndarray:
    """Map RGB mask to HxW class IDs using DANISH_PALETTE."""
    h, w = mask_rgb.shape[:2]
    out = np.zeros((h, w), dtype=np.int64)
    for cid, rgb in enumerate(DANISH_PALETTE):
        match = (
            (mask_rgb[..., 0] == rgb[0])
            & (mask_rgb[..., 1] == rgb[1])
            & (mask_rgb[..., 2] == rgb[2])
        )
        out[match] = cid
    return out


def _list_pairs_from_zip(zip_path: Path) -> List[Tuple[str, str]]:
    """List (orthophoto_path, mask_path) inside archive."""
    pairs: List[Tuple[str, str]] = []
    prefix_img = ORTHO_DIR + "/"
    prefix_mask = MASK_DIR + "/"
    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
    img_names = [n for n in namelist if n.startswith(prefix_img) and n.endswith(".jpg")]
    for img_name in sorted(img_names):
        base = img_name[len(prefix_img) : -4]  # strip prefix and .jpg
        mask_name = prefix_mask + base + ".png"
        if mask_name in namelist:
            pairs.append((img_name, mask_name))
    return pairs


def extract_danish_archive(archive_path: Path, out_dir: Path) -> Path:
    """Extract orthophotos and masks to out_dir/orthophotos and out_dir/masks. Returns out_dir."""
    archive_path = Path(archive_path)
    out_dir = Path(out_dir)
    ortho_out = out_dir / "orthophotos"
    mask_out = out_dir / "masks"
    ortho_out.mkdir(parents=True, exist_ok=True)
    mask_out.mkdir(parents=True, exist_ok=True)
    pairs = _list_pairs_from_zip(archive_path)
    with zipfile.ZipFile(archive_path, "r") as zf:
        for img_name, mask_name in pairs:
            base = Path(img_name).stem
            zf.extract(img_name, out_dir)
            (out_dir / img_name).rename(ortho_out / (base + ".jpg"))
            zf.extract(mask_name, out_dir)
            (out_dir / mask_name).rename(mask_out / (base + ".png"))
    for d in (out_dir / ORTHO_DIR, out_dir / MASK_DIR):
        if d.exists():
            d.rmdir()
    return out_dir


def load_danish_from_zip(
    archive_path: Path,
    tile_size: int = 512,
    limit: Optional[int] = None,
    val_ratio: float = 0.1,
    seed: int = 42,
) -> Tuple[Iterator[Tuple[np.ndarray, np.ndarray]], Iterator[Tuple[np.ndarray, np.ndarray]]]:
    """
    Load Danish Golf Courses from archive.zip.
    
    Returns (train_iterator, val_iterator). Each yields (image, mask) where
    image is RGB (H, W, 3), mask is (H, W) class IDs 0..5.
    """
    archive_path = Path(archive_path)
    if not archive_path.exists():
        raise FileNotFoundError(f"Archive not found: {archive_path}")

    pairs = _list_pairs_from_zip(archive_path)
    if not pairs:
        raise ValueError(f"No image/mask pairs found in {archive_path}")

    rng = np.random.default_rng(seed)
    rng.shuffle(pairs)
    n = len(pairs)
    nval = max(1, int(n * val_ratio))
    ntrain = n - nval
    train_pairs = pairs[:ntrain]
    val_pairs = pairs[ntrain : ntrain + nval]

    if limit is not None:
        train_pairs = train_pairs[: limit]
        val_pairs = val_pairs[: max(1, limit // 10)]

    def _iter(pair_list: List[Tuple[str, str]], lim: Optional[int]) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
        count = 0
        with zipfile.ZipFile(archive_path, "r") as zf:
            for img_name, mask_name in pair_list:
                if lim is not None and count >= lim:
                    break
                try:
                    with zf.open(img_name) as f:
                        img = np.array(Image.open(f).convert("RGB"))
                    with zf.open(mask_name) as f:
                        mask_rgb = np.array(Image.open(f))
                except Exception:
                    continue
                if mask_rgb.ndim != 3:
                    continue
                mask = _rgb_to_class_id(mask_rgb)
                h, w = img.shape[:2]
                if tile_size > 0 and (h != tile_size or w != tile_size):
                    for (timg, tmask) in _tile_crop(img, mask, tile_size):
                        if lim is not None and count >= lim:
                            return
                        count += 1
                        yield timg, tmask
                else:
                    count += 1
                    yield img, mask

    return (
        _iter(train_pairs, limit),
        _iter(val_pairs, None if limit is None else max(1, (limit or 0) // 10)),
    )


class DanishGolfDataset:
    """PyTorch-friendly dataset over extracted Danish orthophotos + masks."""

    def __init__(
        self,
        extract_dir: Path,
        tile_size: int = 512,
        split: str = "all",
        val_ratio: float = 0.1,
        limit: Optional[int] = None,
        seed: int = 42,
    ):
        self.extract_dir = Path(extract_dir)
        self.tile_size = tile_size
        self.split = split
        ortho = self.extract_dir / "orthophotos"
        mask = self.extract_dir / "masks"
        if not ortho.exists() or not mask.exists():
            raise FileNotFoundError(
                f"Extract Danish archive to {extract_dir} first "
                "(orthophotos/ and masks/ dirs)."
            )
        stems = sorted(p.stem for p in ortho.glob("*.jpg") if (mask / (p.stem + ".png")).exists())
        rng = np.random.default_rng(seed)
        rng.shuffle(stems)
        if split != "all":
            nval = max(1, int(len(stems) * val_ratio))
            stems = stems[:-nval] if split == "train" else stems[-nval:]
        if limit is not None:
            stems = stems[:limit]
        self.stems = stems
        self._tile_cache: List[Tuple[Path, Path, int, int]] = []
        self._build_tile_index()

    def _build_tile_index(self) -> None:
        """Build list of (img_path, mask_path, y, x) for each tile."""
        from PIL import Image
        self._tile_cache.clear()
        for s in self.stems:
            imp = self.extract_dir / "orthophotos" / (s + ".jpg")
            msp = self.extract_dir / "masks" / (s + ".png")
            with Image.open(imp) as im:
                w, h = im.size
            step = self.tile_size
            for y in range(0, h, step):
                for x in range(0, w, step):
                    self._tile_cache.append((imp, msp, y, x))

    def __len__(self) -> int:
        return len(self._tile_cache)

    def __getitem__(self, idx: int) -> Tuple[np.ndarray, np.ndarray]:
        imp, msp, y, x = self._tile_cache[idx]
        img = np.array(Image.open(imp).convert("RGB"))
        mask_rgb = np.array(Image.open(msp))
        mask = _rgb_to_class_id(mask_rgb)
        size = self.tile_size
        h, w = img.shape[:2]
        y1, x1 = min(y + size, h), min(x + size, w)
        timg = img[y:y1, x:x1]
        tmask = mask[y:y1, x:x1]
        if timg.shape[0] < size or timg.shape[1] < size:
            pad_h = size - timg.shape[0]
            pad_w = size - timg.shape[1]
            timg = np.pad(timg, ((0, pad_h), (0, pad_w), (0, 0)), mode="edge")
            tmask = np.pad(tmask, ((0, pad_h), (0, pad_w)), constant_values=0)
        return timg, tmask


def _tile_crop(
    img: np.ndarray,
    mask: np.ndarray,
    size: int,
) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
    """Yield non-overlapping tiles of `size`; pad if needed."""
    h, w = img.shape[:2]
    step = size
    for y in range(0, h, step):
        for x in range(0, w, step):
            y1, x1 = min(y + size, h), min(x + size, w)
            timg = img[y:y1, x:x1]
            tmask = mask[y:y1, x:x1]
            if timg.shape[0] < size or timg.shape[1] < size:
                # Pad bottom/right
                pad_h = size - timg.shape[0]
                pad_w = size - timg.shape[1]
                timg = np.pad(timg, ((0, pad_h), (0, pad_w), (0, 0)), mode="edge")
                tmask = np.pad(tmask, ((0, pad_h), (0, pad_w)), constant_values=0)
            else:
                timg = timg.copy()
                tmask = tmask.copy()
            yield timg, tmask
