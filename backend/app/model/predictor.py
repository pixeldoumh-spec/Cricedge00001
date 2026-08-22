"""Prediction boundary for the next-generation CricEdge model.

This module intentionally contains no legacy model logic. The new model will be
implemented behind this stable application-facing interface.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PredictionRequest:
    """Inputs required by the prediction engine."""

    format: str
    home: str
    away: str
    venue: str | None = None


class PredictionEngine:
    """Application boundary for cricket predictions.

    Training, feature engineering, calibration, and artifact loading will be
    implemented behind this interface. Keeping the boundary small lets the API
    remain stable while the model is rebuilt from scratch.
    """

    def predict(self, request: PredictionRequest) -> dict[str, Any]:
        raise NotImplementedError("The new CricEdge prediction model is not implemented yet")

    def train(self, training_source: Any) -> Any:
        raise NotImplementedError("The new CricEdge training pipeline is not implemented yet")
