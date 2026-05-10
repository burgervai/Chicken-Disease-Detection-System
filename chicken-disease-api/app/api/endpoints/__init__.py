"""
API endpoints router
"""
import base64
import hashlib
import json
import uuid
from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import text

from app.schemas import (
    ModelInfo,
    PredictionHistoryResponse,
    PredictionResponse,
    PredictionResult,
)
from app.services.database import db_service
from app.services.model_registry import model_registry
from app.services.notification import notification_service

logger = structlog.get_logger()

router = APIRouter()


def hash_image(data: bytes) -> str:
    """Generate hash for image data."""
    return hashlib.md5(data).hexdigest()


def normalize_disease(value):
    """Convert enum/string disease values into plain strings for storage."""
    if hasattr(value, "value"):
        return value.value
    return str(value)


@router.post("/predict", response_model=PredictionResponse)
async def predict_disease(
    image: UploadFile = File(...),
    model_version: Optional[str] = Form(None),
    threshold: float = Form(0.5, ge=0.0, le=1.0),
):
    """
    Predict disease from chicken fecal image.

    - image: Image file, jpg/jpeg/png
    - model_version: Optional specific model version
    - threshold: Confidence threshold
    """
    try:
        if not image.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        file_ext = image.filename.split(".")[-1].lower()
        if file_ext not in ["jpg", "jpeg", "png"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Allowed: jpg, jpeg, png",
            )

        contents = await image.read()

        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large. Max 10MB")

        image_b64 = base64.b64encode(contents).decode("utf-8")
        start_time = datetime.utcnow()

        result = await model_registry.predict(
            image_data=image_b64,
            model_version=model_version,
            threshold=threshold,
        )

        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        prediction_id = str(uuid.uuid4())
        disease = normalize_disease(result["disease"])
        active_model_version = model_version or model_registry.active_model or "unknown"

        probabilities = {
            str(key): float(value)
            for key, value in result["probabilities"].items()
        }

        async with db_service.get_session() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO predictions (
                        id,
                        image_hash,
                        disease,
                        confidence,
                        probabilities,
                        model_version,
                        processing_time_ms,
                        threshold,
                        created_at,
                        websocket_sent
                    )
                    VALUES (
                        :id,
                        :image_hash,
                        :disease,
                        :confidence,
                        CAST(:probabilities AS JSONB),
                        :model_version,
                        :processing_time_ms,
                        :threshold,
                        :created_at,
                        :websocket_sent
                    )
                    """
                ),
                {
                    "id": prediction_id,
                    "image_hash": hash_image(contents),
                    "disease": disease,
                    "confidence": float(result["confidence"]),
                    "probabilities": json.dumps(probabilities),
                    "model_version": active_model_version,
                    "processing_time_ms": float(
                        result.get("inference_time_ms", processing_time)
                    ),
                    "threshold": float(threshold),
                    "created_at": datetime.utcnow(),
                    "websocket_sent": False,
                },
            )
            await session.commit()

        logger.info(
            "prediction_completed",
            prediction_id=prediction_id,
            disease=disease,
            confidence=result["confidence"],
        )

        return PredictionResponse(
            id=prediction_id,
            result=PredictionResult(
                disease=disease,
                confidence=float(result["confidence"]),
                probabilities=probabilities,
            ),
            model_version=active_model_version,
            processing_time_ms=float(result.get("inference_time_ms", processing_time)),
            created_at=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("prediction_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.get("/predictions/history", response_model=PredictionHistoryResponse)
async def get_prediction_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    model_version: Optional[str] = None,
):
    """Get prediction history with pagination."""
    try:
        offset = (page - 1) * page_size

        async with db_service.get_session() as session:
            if model_version:
                total_result = await session.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM predictions
                        WHERE model_version = :model_version
                        """
                    ),
                    {"model_version": model_version},
                )

                rows_result = await session.execute(
                    text(
                        """
                        SELECT
                            id,
                            disease,
                            confidence,
                            probabilities,
                            model_version,
                            processing_time_ms,
                            created_at
                        FROM predictions
                        WHERE model_version = :model_version
                        ORDER BY created_at DESC
                        LIMIT :limit OFFSET :offset
                        """
                    ),
                    {
                        "model_version": model_version,
                        "limit": page_size,
                        "offset": offset,
                    },
                )
            else:
                total_result = await session.execute(
                    text("SELECT COUNT(*) FROM predictions")
                )

                rows_result = await session.execute(
                    text(
                        """
                        SELECT
                            id,
                            disease,
                            confidence,
                            probabilities,
                            model_version,
                            processing_time_ms,
                            created_at
                        FROM predictions
                        ORDER BY created_at DESC
                        LIMIT :limit OFFSET :offset
                        """
                    ),
                    {
                        "limit": page_size,
                        "offset": offset,
                    },
                )

            total = int(total_result.scalar() or 0)
            rows = rows_result.mappings().all()

        total_pages = (total + page_size - 1) // page_size

        predictions = []
        for row in rows:
            probabilities = row["probabilities"] or {}
            if isinstance(probabilities, str):
                probabilities = json.loads(probabilities)

            predictions.append(
                PredictionResponse(
                    id=str(row["id"]),
                    result=PredictionResult(
                        disease=row["disease"],
                        confidence=float(row["confidence"]),
                        probabilities=probabilities,
                    ),
                    model_version=row["model_version"],
                    processing_time_ms=float(row["processing_time_ms"]),
                    created_at=row["created_at"],
                )
            )

        return PredictionHistoryResponse(
            predictions=predictions,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    except Exception as e:
        logger.error("history_fetch_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch prediction history")


@router.get("/predictions/{prediction_id}", response_model=PredictionResponse)
async def get_prediction(prediction_id: str):
    """Get a specific prediction by ID."""
    try:
        async with db_service.get_session() as session:
            result = await session.execute(
                text(
                    """
                    SELECT
                        id,
                        disease,
                        confidence,
                        probabilities,
                        model_version,
                        processing_time_ms,
                        created_at
                    FROM predictions
                    WHERE id = :id
                    """
                ),
                {"id": prediction_id},
            )

            row = result.mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail="Prediction not found")

        probabilities = row["probabilities"] or {}
        if isinstance(probabilities, str):
            probabilities = json.loads(probabilities)

        return PredictionResponse(
            id=str(row["id"]),
            result=PredictionResult(
                disease=row["disease"],
                confidence=float(row["confidence"]),
                probabilities=probabilities,
            ),
            model_version=row["model_version"],
            processing_time_ms=float(row["processing_time_ms"]),
            created_at=row["created_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("prediction_fetch_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch prediction")


@router.get("/models", response_model=List[ModelInfo])
async def list_models():
    """List all available model versions."""
    await model_registry.initialize()
    models = model_registry.get_available_models()

    return [
        ModelInfo(
            version=model["version"],
            name=model["name"],
            description=model["description"],
            accuracy=model["metrics"].get("accuracy", 0),
            precision=model["metrics"].get("precision", 0),
            recall=model["metrics"].get("recall", 0),
            f1_score=model["metrics"].get("f1_score", 0),
            training_date=datetime.utcnow(),
            dataset_size=0,
            classes=["healthy", "coccidiosis"],
            is_active=(model["version"] == model_registry.active_model),
            status=model["status"],
        )
        for model in models
    ]


@router.get("/models/active")
async def get_active_model():
    """Get information about the active model."""
    await model_registry.initialize()
    model_info = model_registry.get_active_model_info()

    if not model_info:
        raise HTTPException(status_code=404, detail="No active model")

    return ModelInfo(
        version=model_info["version"],
        name=model_info["name"],
        description=model_info["description"],
        accuracy=model_info["metrics"].get("accuracy", 0),
        precision=model_info["metrics"].get("precision", 0),
        recall=model_info["metrics"].get("recall", 0),
        f1_score=model_info["metrics"].get("f1_score", 0),
        training_date=datetime.utcnow(),
        dataset_size=0,
        classes=["healthy", "coccidiosis"],
        is_active=True,
        status=model_info["status"],
    )


@router.post("/models/{version}/activate")
async def activate_model(version: str):
    """Activate a specific model version lazily."""
    try:
        await model_registry.activate_model(version)
        await notification_service.send_model_update_notification(version, "activated")

        return {
            "message": f"Model {version} activated successfully",
            "lazy_loading": True,
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("model_activation_failed", version=version, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to activate model")


@router.get("/statistics")
async def get_statistics():
    """Get prediction statistics."""
    try:
        async with db_service.get_session() as session:
            total_result = await session.execute(
                text("SELECT COUNT(*) FROM predictions")
            )

            result_counts_result = await session.execute(
                text(
                    """
                    SELECT disease, COUNT(*) AS count
                    FROM predictions
                    GROUP BY disease
                    """
                )
            )

            model_counts_result = await session.execute(
                text(
                    """
                    SELECT model_version, COUNT(*) AS count
                    FROM predictions
                    GROUP BY model_version
                    """
                )
            )

            total_predictions = int(total_result.scalar() or 0)
            result_counts = result_counts_result.mappings().all()
            model_counts = model_counts_result.mappings().all()

        return {
            "total_predictions": total_predictions,
            "predictions_by_result": {
                row["disease"]: row["count"]
                for row in result_counts
            },
            "predictions_by_model": {
                row["model_version"]: row["count"]
                for row in model_counts
            },
            "models_loaded": model_registry.get_loaded_models_count(),
        }

    except Exception as e:
        logger.error("statistics_fetch_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")
