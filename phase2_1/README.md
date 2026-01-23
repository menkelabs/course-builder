# Phase 2.1 – SegFormer semantic segmentation

Train SegFormer-B3 on **Danish Golf Courses Orthophotos** (Kaggle), then run inference → masks → polygons → SVG.

## Training

Data: `phase2a/resources/archive.zip` (orthophotos + segmentation masks).

```bash
# From course-builder repo root, using project venv
.venv/bin/python -m phase2_1 train --archive phase2a/resources/archive.zip -o phase2_1_output
```

**Options:**

- `--archive`: Path to `archive.zip` (default: `phase2a/resources/archive.zip`)
- `-o, --output-dir`: Checkpoints and config (default: `phase2_1_output`)
- `--extract-dir`: Where to extract the archive (default: `<output-dir>/danish_extracted`)
- `--tile-size`: 512, 768, or 1024 (default: 512)
- `--epochs`, `--batch-size`, `--lr`: Training hyperparameters
- `--device`: `cuda` or `cpu`
- `--limit`: Limit number of images (for quick tests)
- `-v, --verbose`: Verbose logging

**Example – full training:**

```bash
.venv/bin/python -m phase2_1 train \
  --archive phase2a/resources/archive.zip \
  -o phase2_1_output \
  --tile-size 512 \
  --epochs 50 \
  --batch-size 8 \
  --device cuda
```

**Example – quick sanity check:**

```bash
.venv/bin/python -m phase2_1 train --epochs 1 --batch-size 2 --limit 5 -o /tmp/p21
```

Checkpoints:

- `segformer_b3_danish_best.pt`: best validation mIoU
- `segformer_b3_danish_final.pt`: final epoch
- `train_config.json`: training config

## Configuration

- **Model**: SegFormer-B3 (`nvidia/mit-b3`). Config defaults in `config.SegFormerConfig` use `model_size="b3"`.
- **Classes**: `background`, `fairway`, `green`, `tee`, `bunker`, `water` (Danish palette in `pipeline/dataset.py`).
- **Loss**: Cross-entropy + Dice. Validation: mean IoU over classes.

## Dependencies

```bash
pip install -e ".[train]"
```

Uses `torch`, `transformers`, and project deps (see `pyproject.toml`).
