"""
API endpoints router
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from typing import Optional, List
from datetime import datetime
import uuid

from app.schemas import (
    PredictionRequest,
    PredictionResponse,
    PredictionResult,
    PredictionHistoryResponse,
    ModelInfo,
    ErrorResponse,
)
from app.services.model_registry import model_registry
from app.services.database import db_service
from app.services.notification import notification_service
import structlog

logger = structlog.get_logger()

router = APIRouter()


@router.post("/predict", response_model=PredictionResponse)
async def predict_disease(
    image: UploadFile = File(...),
    model_version: Optional[str] = Form(None),
    threshold: float = Form(0.5, ge=0.0, le=1.0),
):
    """
    Predict disease from chicken fecal image.

    - **image**: Image file (jpg, jpeg, png)
    - **model_version**: Optional specific model version to use
    - **threshold**: Confidence threshold (0.0 - 1.0)
    """
    try:
        # Validate file
        if not image.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        file_ext = image.filename.split(".")[-1].lower()
        if file_ext not in ["jpg", "jpeg", "png"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: jpg, jpeg, png",
            )

        # Read image data
        contents = await image.read()

        # Validate file size
        if len(contents) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")

        # Run prediction
        import base64

        image_b64 = base64.b64encode(contents).decode()
        start_time = datetime.utcnow()

        result = await model_registry.predict(
            image_data=image_b64,
            model_version=model_version,
            threshold=threshold,
        )

        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Create prediction record
        prediction_id = str(uuid.uuid4())
        prediction_record = {
            "_id": prediction_id,
            "image_hash": hash_image(contents),
            "result": {
                "disease": result["disease"],
                "confidence": result["confidence"],
                "probabilities": result["probabilities"],
            },
            "model_version": model_version or model_registry.active_model,
            "processing_time_ms": processing_time,
            "threshold": threshold,
            "created_at": datetime.utcnow(),
            "websocket_sent": False,
        }

        # Store prediction in database
        await db_service.predictions.insert_one(prediction_record)

        logger.info(
            "prediction_completed",
            prediction_id=prediction_id,
            disease=result["disease"],
            confidence=result["confidence"],
        )

        return PredictionResponse(
            id=prediction_id,
            result=PredictionResult(
                disease=result["disease"],
                confidence=result["confidence"],
                probabilities=result["probabilities"],
            ),
            model_version=model_version or model_registry.active_model,
            processing_time_ms=result.get("inference_time_ms", processing_time),
            created_at=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("prediction_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Prediction failed")


def hash_image(data: bytes) -> str:
    """Generate hash for image data"""
    import hashlib
    return hashlib.md5(data).hexdigest()


@router.get("/predictions/history", response_model=PredictionHistoryResponse)
async def get_prediction_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    model_version: Optional[str] = None,
):
    """
    Get prediction history with pagination.

    - **page**: Page number (starts at 1)
    - **page_size**: Number of predictions per page (max 100)
    - **model_version**: Filter by model version (optional)
    """
    try:
        # Build query
        query = {}
        if model_version:
            query["model_version"] = model_version

        # Get total count
        total = await db_service.predictions.count_documents(query)

        # Calculate pagination
        skip = (page - 1) * page_size
        total_pages = (total + page_size - 1) // page_size

        # Get predictions
        cursor = db_service.predictions.find(query).sort("created_at", -1).skip(skip).limit(page_size)
        predictions = await cursor.to_list(length=page_size)

        # Format response
        formatted_predictions = []
        for pred in predictions:
            formatted_predictions.append(
                PredictionResponse(
                    id=str(pred["_id"]),
                    result=PredictionResult(
                        disease=pred["result"]["disease"],
                        confidence=pred["result"]["confidence"],
                        probabilities=pred["result"]["probabilities"],
                    ),
                    model_version=pred["model_version"],
                    processing_time_ms=pred["processing_time_ms"],
                    created_at=pred["created_at"],
                )
            )

        return PredictionHistoryResponse(
            predictions=formatted_predictions,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    except Exception as e:
        logger.error("history_fetch_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch prediction history")


@router.get("/predictions/{prediction_id}")
async def get_prediction(prediction_id: str):
    """Get a specific prediction by ID"""
    try:
        prediction = await db_service.predictions.find_one({"_id": prediction_id})

        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")

        return PredictionResponse(
            id=str(prediction["_id"]),
            result=PredictionResult(
                disease=prediction["result"]["disease"],
                confidence=prediction["result"]["confidence"],
                probabilities=prediction["result"]["probabilities"],
            ),
            model_version=prediction["model_version"],
            processing_time_ms=prediction["processing_time_ms"],
            created_at=prediction["created_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("prediction_fetch_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch prediction")


@router.get("/models", response_model=List[ModelInfo])
async def list_models():
    """List all available model versions"""
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
            training_date=datetime.utcnow(),  # Placeholder
            dataset_size=0,  # Placeholder
            classes=["healthy", "coccidiosis"],
            is_active=(model["version"] == model_registry.active_model),
            status=model["status"],
        )
        for model in models
    ]


@router.get("/models/active")
async def get_active_model():
    """Get information about the currently active model"""
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
    """Activate a specific model version"""
    try:
        await model_registry.activate_model(version)

        # Notify all connected clients
        await notification_service.send_model_update_notification(version, "activated")

        return {"message": f"Model {version} activated successfully"}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("model_activation_failed", version=version, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to activate model")


@router.get("/statistics")
async def get_statistics():
    """Get prediction statistics"""
    try:
        total_predictions = await db_service.predictions.count_documents({})

        # Get predictions by result
        pipeline = [
            {
                "$group": {
                    "_id": "$result.disease",
                    "count": {"$sum": 1},
                }
            }
        ]
        cursor = db_service.predictions.aggregate(pipeline)
        result_counts = await cursor.to_list(length=100)

        # Get predictions by model
        model_pipeline = [
            {
                "$group": {
                    "_id": "$model_version",
                    "count": {"$sum": 1},
                }
            }
        ]
        model_cursor = db_service.predictions.aggregate(model_pipeline)
        model_counts = await model_cursor.to_list(length=100)

        return {
            "total_predictions": total_predictions,
            "predictions_by_result": {rc["_id"]: rc["count"] for rc in result_counts},
            "predictions_by_model": {mc["_id"]: mc["count"] for mc in model_counts},
            "models_loaded": model_registry.get_loaded_models_count(),
        }

    except Exception as e:
        logger.error("statistics_fetch_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")
