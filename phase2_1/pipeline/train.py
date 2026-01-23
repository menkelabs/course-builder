"""SegFormer-B3 training on Danish Golf Courses."""

import json
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, random_split

from ..config import SegFormerConfig

logger = logging.getLogger(__name__)

# course-builder repo root = parents[2] from phase2_1/pipeline/train.py
_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARCHIVE = _REPO_ROOT / "phase2a" / "resources" / "archive.zip"


def _dice_loss(pred: torch.Tensor, target: torch.Tensor, num_classes: int, smooth: float = 1e-6) -> torch.Tensor:
    """Per-class Dice; mean over classes. pred: (N,C,H,W) logits, target: (N,H,W) Long."""
    pred = F.softmax(pred, dim=1)
    n, c, h, w = pred.shape
    target_one = F.one_hot(target.clamp(0, c - 1), num_classes=c).permute(0, 3, 1, 2).float()
    dice = 0.0
    for k in range(c):
        pk = pred[:, k]
        tk = target_one[:, k]
        inter = (pk * tk).sum(dim=(1, 2))
        union = pk.sum(dim=(1, 2)) + tk.sum(dim=(1, 2)) + smooth
        dice += ((2 * inter + smooth) / union).mean()
    return 1.0 - dice / c


class CombinedLoss(nn.Module):
    def __init__(self, num_classes: int, ce_weight: float = 0.5, dice_weight: float = 0.5):
        super().__init__()
        self.num_classes = num_classes
        self.ce_weight = ce_weight
        self.dice_weight = dice_weight
        self.ce = nn.CrossEntropyLoss(ignore_index=255)

    def forward(
        self,
        pred: torch.Tensor,
        target: torch.Tensor,
    ) -> torch.Tensor:
        target = target.long().clamp(0, self.num_classes - 1)
        ce = self.ce(pred, target)
        dice = _dice_loss(pred, target, self.num_classes)
        return self.ce_weight * ce + self.dice_weight * dice


def train(
    archive_path: Path = DEFAULT_ARCHIVE,
    output_dir: Path = Path("phase2_1_output"),
    extract_dir: Optional[Path] = None,
    config: Optional[SegFormerConfig] = None,
    device: str = "cuda",
    seed: int = 42,
    limit: Optional[int] = None,
) -> Path:
    """
    Train SegFormer-B3 on Danish Golf Courses from archive.zip.
    
    Extracts to extract_dir or output_dir/danish_extracted, then trains.
    Saves checkpoints and config to output_dir.
    """
    config = config or SegFormerConfig()
    assert config.model_size.lower() == "b3", "Training uses SegFormer-B3 only."
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(extract_dir) if extract_dir else output_dir / "danish_extracted"

    # Extract if needed
    from .dataset import extract_danish_archive, DanishGolfDataset

    if not (ext / "orthophotos").exists() or not (ext / "masks").exists():
        logger.info("Extracting Danish archive to %s ...", ext)
        extract_danish_archive(Path(archive_path), ext)

    # Dataset (all stems, tile-level train/val split)
    full = DanishGolfDataset(
        extract_dir=ext,
        tile_size=config.input_size,
        split="all",
        val_ratio=0.1,
        limit=limit,
        seed=seed,
    )
    nval = max(1, len(full) // 10)
    ntrain = len(full) - nval
    train_ds, val_ds = random_split(
        full, [ntrain, nval], generator=torch.Generator().manual_seed(seed)
    )

    def _collate(batch):
        imgs = torch.from_numpy(np.stack([b[0] for b in batch])).permute(0, 3, 1, 2).float() / 255.0
        masks = torch.from_numpy(np.stack([b[1] for b in batch])).long()
        return imgs, masks

    loader = DataLoader(
        train_ds,
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=0,
        collate_fn=_collate,
        pin_memory=(device == "cuda"),
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=0,
        collate_fn=_collate,
    )

    # Model
    from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor

    model_name = f"nvidia/mit-{config.model_size}"
    processor = SegformerImageProcessor.from_pretrained(model_name)
    model = SegformerForSemanticSegmentation.from_pretrained(
        model_name,
        num_labels=config.num_classes,
        semantic_loss_ignore_index=255,
    )
    model.to(device)

    opt = torch.optim.AdamW(model.parameters(), lr=config.learning_rate)
    criterion = CombinedLoss(config.num_classes, ce_weight=0.5, dice_weight=0.5)
    num_classes = config.num_classes

    # Training loop (processor expects 0–255 PIL-like; we use raw tensors and resize inside)
    def _prepare(imgs: torch.Tensor, masks: torch.Tensor):
        """imgs (N,3,H,W) 0–1, masks (N,H,W). Resize to model expectations, normalize."""
        from torchvision import transforms as T
        size = (config.input_size, config.input_size)
        imgs = F.interpolate(imgs, size=size, mode="bilinear", align_corners=False)
        masks = F.interpolate(
            masks.unsqueeze(1).float(),
            size=size,
            mode="nearest",
        ).squeeze(1).long()
        # SegFormer ImageProcessor normalizes with ImageNet stats
        normalize = T.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        )
        imgs = normalize(imgs)
        return imgs, masks

    best_miou = -1.0
    ckpt = output_dir / "segformer_b3_danish_best.pt"
    for ep in range(config.epochs):
        model.train()
        train_loss = 0.0
        for imgs, masks in loader:
            imgs, masks = imgs.to(device), masks.to(device)
            imgs, masks = _prepare(imgs, masks)
            opt.zero_grad()
            out = model(pixel_values=imgs)
            logits = out.logits  # (N, C, h, w)
            logits = F.interpolate(logits, size=masks.shape[-2:], mode="bilinear", align_corners=False)
            loss = criterion(logits, masks)
            loss.backward()
            opt.step()
            train_loss += loss.item()
        train_loss /= max(1, len(loader))

        # Validation IoU
        model.eval()
        ious = []
        with torch.no_grad():
            for imgs, masks in val_loader:
                imgs, masks = imgs.to(device), masks.to(device)
                imgs, masks = _prepare(imgs, masks)
                out = model(pixel_values=imgs)
                logits = out.logits
                logits = F.interpolate(logits, size=masks.shape[-2:], mode="bilinear", align_corners=False)
                pred = logits.argmax(dim=1)
                for c in range(num_classes):
                    mask_c = masks == c
                    pred_c = pred == c
                    inter = (mask_c & pred_c).float().sum().item()
                    union = (mask_c | pred_c).float().sum().item()
                    if union > 0:
                        ious.append(inter / union)
        miou = float(np.mean(ious)) if ious else 0.0
        if miou > best_miou:
            best_miou = miou
            ckpt = output_dir / "segformer_b3_danish_best.pt"
            torch.save(
                {"model": model.state_dict(), "config": config, "epoch": ep, "miou": miou},
                ckpt,
            )
            logger.info("Saved best checkpoint %s (mIoU %.4f)", ckpt, miou)

        logger.info("Epoch %d train_loss=%.4f val_mIoU=%.4f", ep + 1, train_loss, miou)

    # Save final checkpoint
    final = output_dir / "segformer_b3_danish_final.pt"
    torch.save(
        {"model": model.state_dict(), "config": config, "epoch": config.epochs - 1, "miou": best_miou},
        final,
    )
    cfg_path = output_dir / "train_config.json"
    with open(cfg_path, "w") as f:
        json.dump(
            {
                "model_size": config.model_size,
                "input_size": config.input_size,
                "num_classes": config.num_classes,
                "epochs": config.epochs,
                "batch_size": config.batch_size,
                "learning_rate": config.learning_rate,
                "archive": str(archive_path),
                "extract_dir": str(ext),
            },
            f,
            indent=2,
        )
    logger.info("Training done. Best mIoU=%.4f. Checkpoints: %s, %s", best_miou, ckpt, final)
    return output_dir
