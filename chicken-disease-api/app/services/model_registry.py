"""
Lazy model registry with versioning support.

Important:
- Does not load TensorFlow/Keras models during app startup.
- Loads the active model only when prediction is requested.
- Avoids creating/saving placeholder models on Render Free.
"""
import base64
import gc
import io
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import structlog
from PIL import Image

from app.core.config import settings
from app.schemas import DiseaseClass, ModelStatus

logger = structlog.get_logger()


class ModelVersion:
    """Represents a single model version."""

    def __init__(
        self,
        version: str,
        model_path: str,
        name: str,
        description: str = "",
        metrics: Optional[Dict] = None,
    ):
        self.version = version
        self.model_path = model_path
        self.name = name
        self.description = description
        self.metrics = metrics or {}
        self.model = None
        self.status = ModelStatus.UNLOADED
        self.loaded_at: Optional[datetime] = None
        self.inference_count = 0

    async def load(self):
        """Load the model into memory only when needed."""
        if self.model is not None and self.status == ModelStatus.READY:
            return

        try:
            logger.info("lazy_loading_model", version=self.version, path=self.model_path)

            # Import TensorFlow lazily so startup uses less memory.
            from tensorflow.keras.models import load_model

            self.model = load_model(self.model_path)
            self.status = ModelStatus.READY
            self.loaded_at = datetime.utcnow()

            logger.info("model_loaded", version=self.version)

        except Exception as e:
            self.status = ModelStatus.ERROR
            logger.error("model_load_failed", version=self.version, error=str(e))
            raise

    async def unload(self):
        """Unload model from memory."""
        if self.model is not None:
            del self.model
            self.model = None
            gc.collect()

        self.status = ModelStatus.UNLOADED
        self.loaded_at = None
        logger.info("model_unloaded", version=self.version)

    async def predict(self, img_array: np.ndarray) -> Dict[str, Any]:
        """Run inference on the model. Loads model lazily if needed."""
        if self.model is None or self.status != ModelStatus.READY:
            await self.load()

        start_time = time.time()

        try:
            predictions = self.model.predict(img_array, verbose=0)
            inference_time = (time.time() - start_time) * 1000

            if len(predictions.shape) > 1:
                pred_probs = predictions[0]
            else:
                pred_probs = predictions

            pred_idx = int(np.argmax(pred_probs))
            confidence = float(pred_probs[pred_idx])

            disease_map = {
                0: DiseaseClass.HEALTHY,
                1: DiseaseClass.COCCIDIOSIS,
            }

            disease = disease_map.get(pred_idx, DiseaseClass.UNKNOWN)

            probabilities = {
                str(disease_map.get(i, f"class_{i}")): float(pred_probs[i])
                for i in range(len(pred_probs))
            }

            self.inference_count += 1

            return {
                "disease": disease,
                "confidence": confidence,
                "probabilities": probabilities,
                "inference_time_ms": inference_time,
            }

        except Exception as e:
            logger.error("inference_failed", version=self.version, error=str(e))
            raise

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "metrics": self.metrics,
            "status": self.status,
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
            "inference_count": self.inference_count,
        }


class ModelRegistry:
    """
    Model registry with lazy loading.

    Startup behavior:
    - Scans model folder.
    - Registers model metadata.
    - Does NOT load TensorFlow model into memory.
    """

    def __init__(self):
        self.models: Dict[str, ModelVersion] = {}
        self.active_model: Optional[str] = None

    async def initialize(self):
        """
        Initialize registry metadata only.

        This is safe to call, but for Render Free you can also skip calling this
        from main.py and let predict() initialize lazily.
        """
        if self.models:
            return

        logger.info("initializing_model_registry_metadata_only")

        models_dir = Path(settings.MODEL_PATH)

        if models_dir.exists():
            for model_file in models_dir.glob("*.h5"):
                version = model_file.stem.replace("model_", "")
                await self.register_model(
                    version=version,
                    model_path=str(model_file),
                    name=f"Chicken Disease Model v{version}",
                    description=f"CNN model for chicken disease classification v{version}",
                    metrics={
                        "accuracy": 0,
                        "precision": 0,
                        "recall": 0,
                        "f1_score": 0,
                    },
                )

            for model_file in models_dir.glob("*.keras"):
                version = model_file.stem.replace("model_", "")
                if version not in self.models:
                    await self.register_model(
                        version=version,
                        model_path=str(model_file),
                        name=f"Chicken Disease Model v{version}",
                        description=f"Keras model for chicken disease classification v{version}",
                        metrics={
                            "accuracy": 0,
                            "precision": 0,
                            "recall": 0,
                            "f1_score": 0,
                        },
                    )

        if not self.models:
            logger.warning(
                "no_model_files_found",
                model_path=settings.MODEL_PATH,
            )
            return

        default_version = settings.DEFAULT_MODEL_VERSION

        if default_version in self.models:
            self.active_model = default_version
        else:
            self.active_model = list(self.models.keys())[0]

        logger.info(
            "model_registry_initialized_metadata_only",
            models_count=len(self.models),
            active_model=self.active_model,
        )

    async def register_model(
        self,
        version: str,
        model_path: str,
        name: str,
        description: str = "",
        metrics: Optional[Dict] = None,
    ):
        """Register a model version without loading it."""
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")

        model = ModelVersion(
            version=version,
            model_path=model_path,
            name=name,
            description=description,
            metrics=metrics,
        )

        self.models[version] = model
        logger.info("model_registered", version=version, path=model_path)

    async def activate_model(self, version: str):
        """
        Activate a model version without loading it.

        The model will load only when predict() is called.
        """
        await self.initialize()

        if version not in self.models:
            raise ValueError(f"Model version {version} not found")

        self.active_model = version
        logger.info("model_activated_lazy", version=version)

    async def deactivate_model(self, version: str):
        """Unload a model from memory."""
        if version in self.models:
            await self.models[version].unload()

        logger.info("model_deactivated", version=version)

    async def predict(
        self,
        image_data: str,
        model_version: Optional[str] = None,
        threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """Run prediction on an image. Loads model lazily."""
        await self.initialize()

        if not self.models:
            raise RuntimeError(
                f"No model files found in {settings.MODEL_PATH}. "
                "Add a .h5 or .keras model file to this directory."
            )

        version = model_version or self.active_model

        if not version:
            raise RuntimeError("No active model is configured")

        if version not in self.models:
            raise ValueError(f"Model version {version} not registered")

        try:
            image_bytes = base64.b64decode(image_data)
            img = Image.open(io.BytesIO(image_bytes))
            img = img.convert("RGB")
            img = img.resize((settings.MODEL_INPUT_SIZE, settings.MODEL_INPUT_SIZE))

            img_array = np.array(img).astype("float32") / 255.0
            img_array = np.expand_dims(img_array, axis=0)

        except Exception as e:
            logger.error("image_decode_failed", error=str(e))
            raise ValueError("Invalid image data")

        result = await self.models[version].predict(img_array)

        if result["confidence"] < threshold:
            result["disease"] = DiseaseClass.UNKNOWN

        return result

    def get_loaded_models_count(self) -> int:
        """Get count of loaded models."""
        return sum(
            1
            for model in self.models.values()
            if model.status == ModelStatus.READY
        )

    def get_available_models(self) -> List[Dict]:
        """Get all registered models."""
        return [model.to_dict() for model in self.models.values()]

    def get_active_model_info(self) -> Optional[Dict]:
        """Get active model metadata."""
        if self.active_model and self.active_model in self.models:
            return self.models[self.active_model].to_dict()
        return None


model_registry = ModelRegistry()
