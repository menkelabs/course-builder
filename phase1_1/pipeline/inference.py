"""SegFormer inference: self-hosted or Roboflow API."""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

from ..config import CLASS_NAMES, InferenceConfig


class SemanticSegmenter:
    """
    Run semantic segmentation inference.
    
    Returns H×W class-ID mask and class_map (id -> name).
    Supports self-hosted (ONNX/Torch) or Roboflow hosted API.
    """

    def __init__(self, config: Optional[InferenceConfig] = None):
        self.config = config or InferenceConfig()
        self._model = None
        self._class_map = dict(CLASS_NAMES)

    def load(self) -> None:
        """Lazy-load model (SegFormer or Roboflow client)."""
        if self._model is not None:
            return
        if self.config.mode == "roboflow":
            self._load_roboflow()
        else:
            self._load_self_hosted()

    def _load_roboflow(self) -> None:
        """Roboflow semantic segmentation API."""
        try:
            from roboflow import Roboflow
        except ImportError:
            raise ImportError(
                "roboflow is required for Roboflow inference. "
                "Install with: pip install roboflow"
            )
        rf = Roboflow(api_key=self.config.roboflow_api_key or "")
        proj = rf.workspace(self.config.roboflow_workspace or "").project(
            self.config.roboflow_project or ""
        )
        self._model = proj.version(1).model  # semantic segmentation version

    def _load_self_hosted(self) -> None:
        """Load SegFormer (transformers) or ONNX from config.model_path."""
        path = self.config.model_path
        if path and Path(path).suffix == ".onnx":
            self._load_onnx(path)
            return
        try:
            import torch
            from transformers import SegformerForSemanticSegmentation
        except ImportError:
            raise ImportError(
                "torch and transformers required for self-hosted inference. "
                "Install with: pip install phase1_1[inference]"
            )
        model_name = f"nvidia/mit-{self.config.model_size}" if hasattr(
            self.config, "model_size"
        ) else "nvidia/mit-b0"
        self._model = SegformerForSemanticSegmentation.from_pretrained(model_name)
        if path:
            state = torch.load(path, map_location="cpu")
            self._model.load_state_dict(state.get("model", state), strict=False)
        self._model.to(self.config.device)
        self._model.eval()

    def _load_onnx(self, path: Path) -> None:
        """Load ONNX model (stub)."""
        try:
            import onnxruntime as ort
        except ImportError:
            raise ImportError("onnxruntime required for ONNX inference.")
        self._model = ort.InferenceSession(
            str(path),
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )

    def predict(
        self,
        image: np.ndarray,
    ) -> Tuple[np.ndarray, Dict[int, str]]:
        """
        Run inference on RGB image (H, W, 3).
        
        Returns:
            mask: H×W int array of class IDs
            class_map: {id: name}
        """
        self.load()
        if self.config.mode == "roboflow":
            return self._predict_roboflow(image)
        return self._predict_self_hosted(image)

    def _predict_roboflow(self, image: np.ndarray) -> Tuple[np.ndarray, Dict[int, str]]:
        """Call Roboflow API; return class-ID mask + class_map."""
        from PIL import Image
        from roboflow import Roboflow  # noqa: F811

        pil = Image.fromarray(image)
        out = self._model.predict(pil, confidence=0.5)
        # Roboflow semantic segmentation returns mask + class_map
        # Adapt to our (mask, class_map) format
        mask = np.array(out.mask) if hasattr(out, "mask") else np.zeros(
            (image.shape[0], image.shape[1]), dtype=np.int64
        )
        cm: Dict[int, str] = getattr(out, "class_map", None) or dict(self._class_map)
        return mask, cm

    def _predict_self_hosted(self, image: np.ndarray) -> Tuple[np.ndarray, Dict[int, str]]:
        """SegFormer inference."""
        import torch
        from torch import nn
        from transformers import SegformerImageProcessor

        processor = SegformerImageProcessor.from_pretrained("nvidia/mit-b0")
        inputs = processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self.config.device) for k, v in inputs.items()}

        with torch.no_grad():
            logits = self._model(**inputs).logits

        if logits.shape[1] != len(self._class_map):
            logits = logits[:, : len(self._class_map), :, :]
        upsampled = nn.functional.interpolate(
            logits,
            size=image.shape[:2],
            mode="bilinear",
            align_corners=False,
        )
        mask = upsampled.argmax(dim=1).squeeze(0).cpu().numpy().astype(np.int64)
        return mask, dict(self._class_map)
