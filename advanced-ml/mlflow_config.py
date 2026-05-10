# MLflow configuration for model tracking
import os
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

@dataclass
class MLflowConfig:
    """Configuration for MLflow tracking"""
    tracking_uri: str
    artifact_root: str
    experiment_name: str = "chicken-disease-classification"
    registry_uri: Optional[str] = None

# Initialize MLflow configuration
def get_mlflow_config() -> MLflowConfig:
    return MLflowConfig(
        tracking_uri=os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"),
        artifact_root=os.getenv("MLFLOW_ARTIFACT_ROOT", "gs://chicken-disease-mlflow/artifacts"),
        registry_uri=os.getenv("MLFLOW_REGISTRY_URI", "http://mlflow:5000"),
        experiment_name=os.getenv("MLFLOW_EXPERIMENT_NAME", "chicken-disease-classification")
    )

def setup_mlflow():
    """Setup MLflow with proper configuration"""
    import mlflow
    from mlflow.tracking import MlflowClient

    config = get_mlflow_config()

    # Set tracking URI
    mlflow.set_tracking_uri(config.tracking_uri)

    # Set or create experiment
    experiment = mlflow.get_experiment_by_name(config.experiment_name)
    if experiment is None:
        mlflow.create_experiment(
            config.experiment_name,
            artifact_location=f"{config.artifact_root}/{config.experiment_name}"
        )
    mlflow.set_experiment(config.experiment_name)

    # Setup model registry if available
    if config.registry_uri:
        mlflow.set_registry_uri(config.registry_uri)

    return MlflowClient()

def log_model_run(
    model_name: str,
    model_type: str,
    metrics: Dict[str, float],
    params: Dict[str, Any],
    artifacts: Optional[Dict[str, str]] = None
) -> str:
    """Log a model training run to MLflow"""
    import mlflow

    config = get_mlflow_config()

    with mlflow.start_run(run_name=f"{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}") as run:
        # Log parameters
        mlflow.log_params(params)

        # Log metrics
        mlflow.log_metrics(metrics)

        # Log model
        if model_type == "tensorflow":
            mlflow.tensorflow.log_model(
                model,
                artifact_path="model",
                registered_model_name=model_name
            )
        elif model_type == "pytorch":
            mlflow.pytorch.log_model(
                model,
                artifact_path="model",
                registered_model_name=model_name
            )
        elif model_type == "sklearn":
            mlflow.sklearn.log_model(
                model,
                artifact_path="model",
                registered_model_name=model_name
            )

        # Log additional artifacts
        if artifacts:
            for name, path in artifacts.items():
                mlflow.log_artifact(path, artifact_path=name)

        return run.info.run_id

# Model versioning and registration
def register_production_model(
    model_name: str,
    model_version: int,
    description: str = "",
    metrics: Optional[Dict[str, float]] = None
):
    """Register a model version as production-ready"""
    from mlflow.tracking import MlflowClient

    client = MlflowClient()

    # Update model version description
    client.update_model_version(
        name=model_name,
        version=model_version,
        description=description
    )

    # Add metrics as tags
    if metrics:
        tags = {f"metric_{k}": str(v) for k, v in metrics.items()}
        tags["production_ready"] = "true"
        tags["registered_at"] = datetime.now().isoformat()
        client.set_model_version_tags(model_name, model_version, tags)

    # Transition to Production if metrics are good
    if metrics and metrics.get("accuracy", 0) >= 0.9:
        client.transition_model_version_stage(
            model_name,
            model_version,
            stage="Production"
        )

def get_production_model(model_name: str) -> Optional[str]:
    """Get the path to the current production model"""
    from mlflow.tracking import MlflowClient

    client = MlflowClient()

    # Get production version
    try:
        versions = client.get_latest_versions(model_name, stages=["Production"])
        if versions:
            return versions[0].source
    except Exception:
        pass

    # Fallback to staging or latest
    try:
        versions = client.get_latest_versions(model_name, stages=["Staging"])
        if versions:
            return versions[0].source
    except Exception:
        pass

    try:
        versions = client.get_latest_versions(model_name)
        if versions:
            return versions[0].source
    except Exception:
        return None

def compare_models(model_name: str, versions: list) -> Dict:
    """Compare metrics across model versions"""
    from mlflow.tracking import MlflowClient

    client = MlflowClient()
    comparison = {}

    for version in versions:
        run = client.get_model_version(model_name, version)
        metrics = client.get_run(run.run_id).data.metrics
        comparison[f"v{version}"] = {
            "accuracy": metrics.get("accuracy", 0),
            "f1_score": metrics.get("f1_score", 0),
            "precision": metrics.get("precision", 0),
            "recall": metrics.get("recall", 0),
            "training_time": metrics.get("training_time", 0),
            "model_size": metrics.get("model_size", 0)
        }

    return comparison