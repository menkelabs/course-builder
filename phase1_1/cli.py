"""Phase 1.1 CLI: train SegFormer-B3 on Danish Golf Courses."""

import logging
from pathlib import Path

import click

from .config import SegFormerConfig

_LOG = logging.getLogger(__name__)


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s %(message)s",
    )


@click.group()
@click.version_option(version="0.1.0", prog_name="phase1_1")
def cli():
    """Phase 1.1 – SegFormer semantic segmentation for golf courses."""
    pass


@cli.command("train")
@click.option(
    "--archive",
    type=click.Path(path_type=Path, exists=True),
    default=Path(__file__).resolve().parents[1].parent / "phase1a" / "resources" / "archive.zip",  # course-builder repo
    help="Path to Danish Golf Courses archive.zip",
)
@click.option(
    "-o", "--output-dir",
    type=click.Path(path_type=Path),
    default=Path("phase1_1_output"),
    help="Output directory for checkpoints and config",
)
@click.option(
    "--extract-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Where to extract archive (default: <output-dir>/danish_extracted)",
)
@click.option("--tile-size", type=int, default=512, help="Input tile size (512, 768, or 1024)")
@click.option("--epochs", type=int, default=50, help="Training epochs")
@click.option("--batch-size", type=int, default=8, help="Batch size")
@click.option("--lr", "learning_rate", type=float, default=6e-5, help="Learning rate")
@click.option("--device", type=click.Choice(["cuda", "cpu"]), default="cuda")
@click.option("--seed", type=int, default=42)
@click.option("--limit", type=int, default=None, help="Limit train samples (for quick tests)")
@click.option("-v", "--verbose", is_flag=True, help="Verbose logging")
def train_cmd(
    archive: Path,
    output_dir: Path,
    extract_dir: Path | None,
    tile_size: int,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    device: str,
    seed: int,
    limit: int | None,
    verbose: bool,
) -> None:
    """Train SegFormer-B3 on Danish Golf Courses (archive.zip)."""
    _setup_logging(verbose)
    cfg = SegFormerConfig(
        model_size="b3",
        input_size=tile_size,
        learning_rate=learning_rate,
        batch_size=batch_size,
        epochs=epochs,
    )
    from .pipeline.train import train
    train(
        archive_path=archive,
        output_dir=output_dir,
        extract_dir=extract_dir,
        config=cfg,
        device=device,
        seed=seed,
        limit=limit,
    )


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
