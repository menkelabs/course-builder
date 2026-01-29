# Archived: Python Agent Phase1 Actions

Phase1 (geocoding, DEM download, heightmap) actions for the Python agent. **Archived** in favor of SegFormer-focused work only.

The active **python-agent** now exposes **Phase 1A** actions only (SegFormer + SAM: `phase1a_run`, `phase1a_generate_masks`, etc.). Phase1 terrain-prep actions were removed.

See `phase1_actions.py` for the original implementation. The underlying pipeline lived in `archive/phase1` (QGIS-based).
