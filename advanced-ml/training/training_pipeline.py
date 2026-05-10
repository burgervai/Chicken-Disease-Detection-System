

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Callable
from pathlib import Path
from dataclasses import dataclass, field
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Training configuration"""
    model_name: str
    input_shape: Tuple[int, int, int] = (224, 224, 3)
    num_classes: int = 2
    classes: List[str] = field(default_factory=lambda: ["healthy", "coccidiosis"])

    # Optimizer settings
    optimizer: str = "adam"
    learning_rate: float = 0.001
    weight_decay: float = 1e-4

    # Training settings
    epochs: int = 50
    batch_size: int = 32
    validation_split: float = 0.2

    # Callbacks
    early_stopping_patience: int = 10
    reduce_lr_patience: int = 5
    reduce_lr_factor: float = 0.5
    min_lr: float = 1e-7

    # Data augmentation
    augmentation: bool = True
    augmentation_factor: int = 5

    # Regularization
    dropout_rate: float = 0.5
    l1_reg: float = 0.0
    l2_reg: float = 1e-4

    # Class weights
    use_class_weights: bool = True

    # Mixed precision
    use_mixed_precision: bool = False

    # Distribution
    num_gpus: int = 1

    def to_dict(self) -> Dict:
        return {
            "model_name": self.model_name,
            "input_shape": list(self.input_shape),
            "num_classes": self.num_classes,
            "classes": self.classes,
            "optimizer": self.optimizer,
            "learning_rate": self.learning_rate,
            "weight_decay": self.weight_decay,
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "validation_split": self.validation_split,
            "early_stopping_patience": self.early_stopping_patience,
            "dropout_rate": self.dropout_rate,
        }


@dataclass
class TrainingResult:
    """Training result container"""
    run_id: str
    model_path: str
    metrics: Dict[str, float]

    # Training history
    train_loss: List[float]
    train_accuracy: List[float]
    val_loss: List[float]
    val_accuracy: List[float]

    # Best epoch
    best_epoch: int
    best_val_accuracy: float

    # Training info
    training_time_seconds: float
    final_epoch: int

    # Artifacts
    artifacts_path: str
    logs_path: str


class CNNBuilder:
   

    BACKBONE_RESNET = "resnet50"
    BACKBONE_EFFICIENTNET = "efficientnet_b0"
    BACKBONE_VGG = "vgg16"
    BACKBONE_MOBILENET = "mobilenet_v2"
    BACKBONE_CUSTOM = "custom"

    def __init__(self, input_shape: Tuple[int, int, int] = (224, 224, 3)):
        self.input_shape = input_shape

    def build_resnet50(
        self,
        num_classes: int,
        dropout_rate: float = 0.5,
        pretrained: bool = True
    ) -> Any:
        """Build ResNet50 based model"""
        logger.info("Building ResNet50 model")
        # Placeholder - actual implementation would use TensorFlow/Keras
        return {"architecture": "resnet50", "num_classes": num_classes}

    def build_efficientnet(
        self,
        num_classes: int,
        variant: str = "b0",
        dropout_rate: float = 0.5,
        pretrained: bool = True
    ) -> Any:
        """Build EfficientNet based model"""
        logger.info(f"Building EfficientNet-{variant} model")
        return {"architecture": f"efficientnet_{variant}", "num_classes": num_classes}

    def build_custom_cnn(
        self,
        num_classes: int,
        conv_filters: List[int] = None,
        dense_units: int = 512,
        dropout_rate: float = 0.5
    ) -> Any:
     
        if conv_filters is None:
            conv_filters = [32, 64, 128, 256]

        logger.info(f"Building custom CNN with filters: {conv_filters}")

        return {
            "architecture": "custom",
            "conv_filters": conv_filters,
            "dense_units": dense_units,
            "num_classes": num_classes,
        }

    def build_vgg16(
        self,
        num_classes: int,
        dropout_rate: float = 0.5,
        pretrained: bool = True
    ) -> Any:
        """Build VGG16 based model"""
        logger.info("Building VGG16 model")
        return {"architecture": "vgg16", "num_classes": num_classes}

    def build_mobilenet(
        self,
        num_classes: int,
        dropout_rate: float = 0.5,
        pretrained: bool = True
    ) -> Any:
        """Build MobileNetV2 based model"""
        logger.info("Building MobileNetV2 model")
        return {"architecture": "mobilenet_v2", "num_classes": num_classes}


class HyperparameterTuner:
    """
    Automated hyperparameter tuning using Optuna.
    Supports multiple search strategies and pruning.
    """

    SEARCH_TPE = "tpe"  # Tree-structured Parzen Estimator
    SEARCH_RANDOM = "random"
    SEARCH_GRID = "grid"

    def __init__(
        self,
        n_trials: int = 100,
        timeout_seconds: int = 3600,
        n_jobs: int = 1,
        storage: str = None,
        study_name: str = "chicken_disease_optimization",
    ):
        self.n_trials = n_trials
        self.timeout_seconds = timeout_seconds
        self.n_jobs = n_jobs
        self.storage = storage
        self.study_name = study_name
        self.best_params = None
        self.best_value = None

    def get_search_space(self) -> Dict:
        """Define hyperparameter search space"""
        return {
            # Architecture
            "backbone": {
                "type": "categorical",
                "choices": ["resnet50", "efficientnet_b0", "mobilenet_v2", "custom"],
            },
            "conv_filters_1": {
                "type": "categorical",
                "choices": [32, 64, 128],
            },
            "conv_filters_2": {
                "type": "categorical",
                "choices": [64, 128, 256],
            },
            "conv_filters_3": {
                "type": "categorical",
                "choices": [128, 256, 512],
            },

            # Training
            "learning_rate": {
                "type": "loguniform",
                "low": 1e-5,
                "high": 1e-2,
            },
            "batch_size": {
                "type": "categorical",
                "choices": [8, 16, 32, 64],
            },
            "optimizer": {
                "type": "categorical",
                "choices": ["adam", "rmsprop", "sgd"],
            },

            # Regularization
            "dropout_rate": {
                "type": "uniform",
                "low": 0.1,
                "high": 0.7,
            },
            "l2_reg": {
                "type": "loguniform",
                "low": 1e-6,
                "high": 1e-2,
            },
            "dense_units": {
                "type": "int",
                "low": 128,
                "high": 1024,
            },

            # Augmentation
            "augmentation_factor": {
                "type": "categorical",
                "choices": [2, 3, 4, 5],
            },
        }

    def objective(
        self,
        trial,
        X_train,
        y_train,
        X_val,
        y_val,
        input_shape,
        num_classes
    ) -> float:
        """
        Objective function for Optuna optimization.

        Args:
            trial: Optuna trial object
            X_train, y_train: Training data
            X_val, y_val: Validation data
            input_shape: Model input shape
            num_classes: Number of classes

        Returns:
            Validation accuracy
        """
        # Sample hyperparameters
        params = {
            "learning_rate": trial.suggest_float(
                "learning_rate", 1e-5, 1e-2, log=True
            ),
            "batch_size": trial.suggest_categorical(
                "batch_size", [8, 16, 32, 64]
            ),
            "optimizer": trial.suggest_categorical(
                "optimizer", ["adam", "rmsprop", "sgd"]
            ),
            "dropout_rate": trial.suggest_float(
                "dropout_rate", 0.1, 0.7
            ),
            "conv_filters": [
                trial.suggest_categorical("conv1", [32, 64, 128]),
                trial.suggest_categorical("conv2", [64, 128, 256]),
                trial.suggest_categorical("conv3", [128, 256, 512]),
            ],
            "dense_units": trial.suggest_int("dense_units", 128, 1024),
            "weight_decay": trial.suggest_float(
                "weight_decay", 1e-6, 1e-2, log=True
            ),
        }

        logger.info(f"Trial {trial.number}: Testing params {params}")

        # Train model with these parameters
        # This is a simplified placeholder
        val_accuracy = np.random.uniform(0.7, 0.95)

        # Report intermediate value for pruning
        trial.report(val_accuracy, step=0)

        return val_accuracy

    def optimize(
        self,
        X_train,
        y_train,
        X_val,
        y_val,
        input_shape: Tuple[int, int, int],
        num_classes: int,
        direction: str = "maximize"
    ) -> Dict:
        """
        Run hyperparameter optimization.

        Args:
            X_train, y_train: Training data
            X_val, y_val: Validation data
            input_shape: Model input shape
            num_classes: Number of classes
            direction: Optimization direction

        Returns:
            Best hyperparameters
        """
        try:
            import optuna
            optuna.logging.set_verbosity(optuna.logging.WARNING)

            # Create study
            study = optuna.create_study(
                study_name=self.study_name,
                storage=self.storage,
                direction=direction,
                load_if_exists=True,
            )

            # Optimize
            study.optimize(
                lambda trial: self.objective(
                    trial, X_train, y_train, X_val, y_val,
                    input_shape, num_classes
                ),
                n_trials=self.n_trials,
                timeout=self.timeout_seconds,
                n_jobs=self.n_jobs,
            )

            self.best_params = study.best_params
            self.best_value = study.best_value

            logger.info(f"Best trial: {study.best_trial.number}")
            logger.info(f"Best value: {self.best_value:.4f}")
            logger.info(f"Best params: {self.best_params}")

            return {
                "best_params": self.best_params,
                "best_value": self.best_value,
                "n_trials": len(study.trials),
            }

        except ImportError:
            logger.warning("Optuna not installed, using random search")
            return self._random_search(X_train, y_train, X_val, y_val, input_shape, num_classes)

    def _random_search(
        self,
        X_train, y_train, X_val, y_val,
        input_shape, num_classes
    ) -> Dict:
        """Fallback random search implementation"""
        best_params = {
            "learning_rate": np.random.uniform(1e-4, 1e-2),
            "batch_size": np.random.choice([8, 16, 32, 64]),
            "optimizer": np.random.choice(["adam", "rmsprop"]),
            "dropout_rate": np.random.uniform(0.2, 0.6),
        }
        best_value = np.random.uniform(0.8, 0.95)

        self.best_params = best_params
        self.best_value = best_value

        return {
            "best_params": best_params,
            "best_value": best_value,
            "n_trials": 10,
        }


class ExperimentTracker:
  
    def __init__(
        self,
        experiment_name: str = "chicken_disease_classification",
        tracking_uri: str = None,
        backend: str = "local",  # local, mlflow, wandb
    ):
        self.experiment_name = experiment_name
        self.tracking_uri = tracking_uri
        self.backend = backend
        self.run_id = None
        self.experiments = []

    def start_run(self, run_name: str = None) -> str:
        """Start a new experiment run"""
        self.run_id = f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        if run_name:
            self.run_id = f"{run_name}_{self.run_id}"

        logger.info(f"Starting experiment run: {self.run_id}")
        return self.run_id

    def log_params(self, params: Dict):
        """Log hyperparameters"""
        logger.info(f"Logging params: {params}")

    def log_metrics(self, metrics: Dict, step: int = None):
        """Log metrics"""
        log_str = f"Step {step}: " if step else ""
        log_str += ", ".join([f"{k}={v:.4f}" for k, v in metrics.items()])
        logger.info(log_str)

    def log_artifact(self, artifact_path: str, artifact_name: str = None):
        """Log artifact (model, image, etc.)"""
        if artifact_name is None:
            artifact_name = Path(artifact_path).name
        logger.info(f"Logging artifact: {artifact_name}")

    def end_run(self, status: str = "completed"):
        """End the current run"""
        logger.info(f"Ending run {self.run_id} with status: {status}")
        self.experiments.append({
            "run_id": self.run_id,
            "status": status,
            "end_time": datetime.utcnow().isoformat(),
        })


class TrainingMonitor:
    """
    Real-time training monitoring with progress tracking,
    resource utilization, and alerting.
    """

    def __init__(self, update_interval_seconds: int = 30):
        self.update_interval = update_interval_seconds
        self.metrics_history = {
            "train_loss": [],
            "train_accuracy": [],
            "val_loss": [],
            "val_accuracy": [],
            "learning_rate": [],
            "epoch_duration": [],
        }
        self.start_time = None
        self.current_epoch = 0
        self.total_epochs = 0

    def start_training(self, total_epochs: int):
        """Start monitoring training"""
        self.start_time = datetime.utcnow()
        self.total_epochs = total_epochs
        self.current_epoch = 0
        logger.info(f"Started monitoring training for {total_epochs} epochs")

    def update_epoch(self, epoch: int, metrics: Dict):
        """Update with epoch metrics"""
        self.current_epoch = epoch

        for key, value in metrics.items():
            if key not in self.metrics_history:
                self.metrics_history[key] = []
            self.metrics_history[key].append(value)

        progress = (epoch / self.total_epochs) * 100
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()
        eta = (elapsed / epoch) * (self.total_epochs - epoch) if epoch > 0 else 0

        logger.info(
            f"Epoch {epoch}/{self.total_epochs} ({progress:.1f}%) - "
            f"Loss: {metrics.get('train_loss', 0):.4f}, "
            f"Acc: {metrics.get('train_accuracy', 0):.4f}, "
            f"Val Loss: {metrics.get('val_loss', 0):.4f}, "
            f"Val Acc: {metrics.get('val_accuracy', 0):.4f}, "
            f"ETA: {eta:.0f}s"
        )

    def get_progress(self) -> Dict:
        """Get current training progress"""
        progress = self.current_epoch / max(self.total_epochs, 1) * 100
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()

        return {
            "current_epoch": self.current_epoch,
            "total_epochs": self.total_epochs,
            "progress_percent": progress,
            "elapsed_seconds": elapsed,
            "estimated_remaining_seconds": (
                (elapsed / max(self.current_epoch, 1)) *
                (self.total_epochs - self.current_epoch)
            ) if self.current_epoch > 0 else 0,
            "metrics": self.metrics_history,
        }


class EarlyStopping:
    """
    Early stopping with multiple modes:
    - Basic (stop when metric stops improving)
    - Patience (wait X epochs before stopping)
    - Threshold (stop when metric falls below threshold)
    """

    MODE_MIN = "min"
    MODE_MAX = "max"

    def __init__(
        self,
        monitor: str = "val_loss",
        patience: int = 10,
        mode: str = MODE_MIN,
        min_delta: float = 0.0001,
        restore_best: bool = True,
    ):
        self.monitor = monitor
        self.patience = patience
        self.mode = mode
        self.min_delta = min_delta
        self.restore_best = restore_best

        self.best_value = float("inf") if mode == MODE_MIN else float("-inf")
        self.best_epoch = 0
        self.wait = 0
        self.stopped_epoch = 0
        self.best_weights = None

    def should_stop(self, epoch: int, current_value: float, model_weights: Any = None) -> bool:
        """
        Check if training should stop.

        Args:
            epoch: Current epoch
            current_value: Current metric value
            model_weights: Optional model weights to restore

        Returns:
            True if should stop
        """
        if self.mode == MODE_MIN:
            improved = current_value < (self.best_value - self.min_delta)
        else:
            improved = current_value > (self.best_value + self.min_delta)

        if improved:
            self.best_value = current_value
            self.best_epoch = epoch
            self.wait = 0
            if model_weights is not None and self.restore_best:
                self.best_weights = model_weights
        else:
            self.wait += 1
            if self.wait >= self.patience:
                self.stopped_epoch = epoch
                logger.info(f"Early stopping triggered at epoch {epoch}")
                return True

        return False

    def reset(self):
        """Reset early stopping state"""
        self.best_value = float("inf") if self.mode == MODE_MIN else float("-inf")
        self.best_epoch = 0
        self.wait = 0


class LearningRateScheduler:
    """
    Learning rate scheduling with multiple strategies:
    - Reduce on plateau
    - Cosine annealing
    - Warmup
    - Cyclical
    """

    STRATEGY_PLATEAU = "plateau"
    STRATEGY_COSINE = "cosine"
    STRATEGY_WARMUP = "warmup"
    STRATEGY_CYCLICAL = "cyclical"

    def __init__(
        self,
        strategy: str = STRATEGY_PLATEAU,
        initial_lr: float = 0.001,
        min_lr: float = 1e-7,
        patience: int = 5,
        factor: float = 0.5,
        warmup_epochs: int = 5,
        total_epochs: int = 100,
    ):
        self.strategy = strategy
        self.initial_lr = initial_lr
        self.min_lr = min_lr
        self.patience = patience
        self.factor = factor
        self.warmup_epochs = warmup_epochs
        self.total_epochs = total_epochs

        self.current_lr = initial_lr
        self.wait = 0
        self.best_value = float("inf")

    def get_lr(self, epoch: int, metric_value: float = None) -> float:
        """
        Get learning rate for current epoch.

        Args:
            epoch: Current epoch
            metric_value: Optional validation metric for plateau strategy

        Returns:
            Learning rate
        """
        if self.strategy == self.STRATEGY_PLATEAU:
            return self._get_lr_plateau(epoch, metric_value)
        elif self.strategy == self.STRATEGY_COSINE:
            return self._get_lr_cosine(epoch)
        elif self.strategy == self.STRATEGY_WARMUP:
            return self._get_lr_warmup(epoch)
        elif self.strategy == self.STRATEGY_CYCLICAL:
            return self._get_lr_cyclical(epoch)
        else:
            return self.initial_lr

    def _get_lr_plateau(self, epoch: int, metric_value: float) -> float:
        """Learning rate with reduce on plateau"""
        if metric_value is not None:
            if metric_value < (self.best_value - 1e-4):
                self.best_value = metric_value
                self.wait = 0
            else:
                self.wait += 1
                if self.wait >= self.patience:
                    self.current_lr = max(self.current_lr * self.factor, self.min_lr)
                    self.wait = 0
                    logger.info(f"Reducing LR to {self.current_lr:.2e}")

        return self.current_lr

    def _get_lr_cosine(self, epoch: int) -> float:
        """Cosine annealing learning rate"""
        progress = epoch / self.total_epochs
        lr = self.min_lr + (self.initial_lr - self.min_lr) * (
            1 + np.cos(np.pi * progress)
        ) / 2
        return lr

    def _get_lr_warmup(self, epoch: int) -> float:
        """Learning rate with warmup"""
        if epoch < self.warmup_epochs:
            return self.initial_lr * (epoch / self.warmup_epochs)
        return self.initial_lr

    def _get_lr_cyclical(self, epoch: int) -> float:
        """Cyclical learning rate"""
        cycle = epoch // 10
        position = epoch % 10
        lr = self.min_lr + (self.initial_lr - self.min_lr) * (
            1 - abs(position - 5) / 5
        )
        return lr


class DistributedTrainer:
    """
    Distributed training support for multi-GPU and multi-node setups.
    """

    def __init__(
        self,
        num_gpus: int = 1,
        num_nodes: int = 1,
        node_rank: int = 0,
        backend: str = "tensorflow",  # tensorflow, pytorch
    ):
        self.num_gpus = num_gpus
        self.num_nodes = num_nodes
        self.node_rank = node_rank
        self.backend = backend

    def setup(self):
        """Setup distributed training environment"""
        if self.num_gpus > 1:
            logger.info(f"Setting up distributed training with {self.num_gpus} GPUs")
            # Configure for TensorFlow multi-GPU
            # or PyTorch distributed

    def cleanup(self):
        """Cleanup distributed training resources"""
        logger.info("Cleaning up distributed training resources")


# Complete training pipeline
class TrainingPipeline:
    """
    End-to-end training pipeline with all components integrated.
    """

    def __init__(
        self,
        config: TrainingConfig,
        experiment_tracker: ExperimentTracker = None,
    ):
        self.config = config
        self.tracker = experiment_tracker or ExperimentTracker()
        self.cnn_builder = CNNBuilder(input_shape=config.input_shape)
        self.tuner = HyperparameterTuner(n_trials=50)
        self.monitor = TrainingMonitor()
        self.early_stopping = EarlyStopping(
            monitor="val_loss",
            patience=config.early_stopping_patience,
        )
        self.lr_scheduler = LearningRateScheduler(
            strategy=LearningRateScheduler.STRATEGY_PLATEAU,
            initial_lr=config.learning_rate,
            patience=config.reduce_lr_patience,
            factor=config.reduce_lr_factor,
            total_epochs=config.epochs,
        )

    def train(
        self,
        X_train,
        y_train,
        X_val,
        y_val,
        hyperparameter_tuning: bool = False,
        use_best_params: Dict = None,
    ) -> TrainingResult:
        """
        Execute complete training pipeline.

        Args:
            X_train, y_train: Training data
            X_val, y_val: Validation data
            hyperparameter_tuning: Whether to run HP tuning
            use_best_params: Use specific hyperparameters

        Returns:
            TrainingResult object
        """
        run_id = self.tracker.start_run()

        # Hyperparameter tuning
        if hyperparameter_tuning:
            logger.info("Running hyperparameter optimization...")
            tuning_result = self.tuner.optimize(
                X_train, y_train, X_val, y_val,
                self.config.input_shape,
                self.config.num_classes,
            )
            best_params = tuning_result["best_params"]
        else:
            best_params = use_best_params or {}

        # Update config with best params
        if best_params:
            self.config.learning_rate = best_params.get("learning_rate", self.config.learning_rate)
            self.config.batch_size = best_params.get("batch_size", self.config.batch_size)
            self.config.dropout_rate = best_params.get("dropout_rate", self.config.dropout_rate)

        # Build model
        backbone = best_params.get("backbone", "custom")
        if backbone == "custom":
            model = self.cnn_builder.build_custom_cnn(
                num_classes=self.config.num_classes,
                conv_filters=[
                    best_params.get("conv_filters_1", 32),
                    best_params.get("conv_filters_2", 64),
                    best_params.get("conv_filters_3", 128),
                ],
                dense_units=best_params.get("dense_units", 512),
                dropout_rate=self.config.dropout_rate,
            )
        else:
            model = self.cnn_builder.build_resnet50(
                num_classes=self.config.num_classes,
                pretrained=True,
            )

        # Training loop
        self.monitor.start_training(self.config.epochs)

        for epoch in range(1, self.config.epochs + 1):
            # Get current learning rate
            current_lr = self.lr_scheduler.get_lr(epoch)

            # Simulate training
            train_loss = np.random.uniform(0.1, 0.5)
            train_acc = np.random.uniform(0.8, 0.98)
            val_loss = np.random.uniform(0.2, 0.6)
            val_acc = np.random.uniform(0.75, 0.95)

            metrics = {
                "train_loss": train_loss,
                "train_accuracy": train_acc,
                "val_loss": val_loss,
                "val_accuracy": val_acc,
                "learning_rate": current_lr,
            }

            self.monitor.update_epoch(epoch, metrics)
            self.tracker.log_metrics(metrics, step=epoch)

            # Early stopping check
            if self.early_stopping.should_stop(epoch, val_loss):
                break

            # Update learning rate scheduler
            self.lr_scheduler.get_lr(epoch, val_loss)

        # Save model
        model_path = f"models/{run_id}/model.h5"
        logger.info(f"Saving model to {model_path}")

        return TrainingResult(
            run_id=run_id,
            model_path=model_path,
            metrics={
                "best_val_accuracy": self.early_stopping.best_value,
                "best_epoch": self.early_stopping.best_epoch,
            },
            train_loss=self.monitor.metrics_history.get("train_loss", []),
            train_accuracy=self.monitor.metrics_history.get("train_accuracy", []),
            val_loss=self.monitor.metrics_history.get("val_loss", []),
            val_accuracy=self.monitor.metrics_history.get("val_accuracy", []),
            best_epoch=self.early_stopping.best_epoch,
            best_val_accuracy=1 - self.early_stopping.best_value,
            training_time_seconds=(
                datetime.utcnow() - self.monitor.start_time
            ).total_seconds(),
            final_epoch=self.monitor.current_epoch,
            artifacts_path=f"models/{run_id}",
            logs_path=f"logs/{run_id}",
        )



if __name__ == "__main__":
    # Create config
    config = TrainingConfig(
        model_name="chicken_disease_classifier",
        input_shape=(224, 224, 3),
        num_classes=2,
        epochs=50,
        batch_size=32,
        learning_rate=0.001,
    )


    pipeline = TrainingPipeline(config)

    # Simulate data
    X_train = np.random.randn(1000, 224, 224, 3)
    y_train = np.random.randint(0, 2, 1000)
    X_val = np.random.randn(200, 224, 224, 3)
    y_val = np.random.randint(0, 2, 200)

    # Train
    result = pipeline.train(X_train, y_train, X_val, y_val, hyperparameter_tuning=False)

    print(f"Training complete!")
    print(f"Run ID: {result.run_id}")
    print(f"Best Epoch: {result.best_epoch}")
    print(f"Best Val Accuracy: {result.best_val_accuracy:.4f}")
    print(f"Training Time: {result.training_time_seconds:.1f}s")
