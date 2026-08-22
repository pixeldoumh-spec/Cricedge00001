"""Model v1: nonlinear gradient-boosted baseline on the frozen v0 feature set."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from sklearn.ensemble import HistGradientBoostingClassifier

FEATURE_NAMES = (
    "team_elo",
    "opponent_elo",
    "elo_difference",
    "team_form_3",
    "team_form_5",
    "team_form_10",
    "venue_team_win_rate",
    "venue_bat_first_win_rate",
    "head_to_head_win_rate",
    "batting_run_rate",
    "bowling_run_rate",
    "batting_wicket_rate",
    "bowling_wicket_rate",
)


@dataclass
class ModelV1:
    """Small, deterministic nonlinear candidate; tuning is intentionally frozen."""

    max_iter: int = 200
    learning_rate: float = 0.05
    max_leaf_nodes: int = 15
    l2_regularization: float = 1.0

    def __post_init__(self) -> None:
        self.estimator = HistGradientBoostingClassifier(
            max_iter=self.max_iter,
            learning_rate=self.learning_rate,
            max_leaf_nodes=self.max_leaf_nodes,
            l2_regularization=self.l2_regularization,
            random_state=0,
        )

    def fit(self, rows: Sequence[dict[str, float]], targets: Sequence[int]) -> "ModelV1":
        self.estimator.fit(self._matrix(rows), targets)
        return self

    def predict_proba(self, rows: Sequence[dict[str, float]]):
        return self.estimator.predict_proba(self._matrix(rows))[:, 1]

    @staticmethod
    def _matrix(rows: Sequence[dict[str, float]]):
        return [[float(row.get(name, 0.0)) for name in FEATURE_NAMES] for row in rows]
