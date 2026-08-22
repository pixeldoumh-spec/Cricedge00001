"""Runtime loading of versioned model artifacts.

Artifacts are deployment inputs, not source-controlled binaries. The registry loads
joblib files from configured directories and never trains or mutates models.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib


@dataclass(frozen=True)
class LoadedArtifact:
    version: str
    model: Any
    calibrator: Any | None
    calibrated: bool


class ArtifactRegistry:
    def __init__(self) -> None:
        self._cache: dict[str, LoadedArtifact] = {}

    def _directory(self, version: str) -> Path:
        env_name = "MODEL_V0_DIR" if version == "v0" else "MODEL_W0_DIR"
        default = Path(__file__).resolve().parents[3] / "models" / version
        return Path(os.getenv(env_name, str(default)))

    def load(self, version: str) -> LoadedArtifact:
        if version in self._cache:
            return self._cache[version]
        directory = self._directory(version)
        model_path = directory / "model.joblib"
        if not model_path.exists():
            raise FileNotFoundError(f"model artifact missing: {model_path}")
        model = joblib.load(model_path)
        calibrator = None
        calibrated = False
        calibrator_path = directory / "calibrator.joblib"
        if calibrator_path.exists():
            calibrator = joblib.load(calibrator_path)
            calibrated = True
        artifact = LoadedArtifact(version, model, calibrator, calibrated)
        self._cache[version] = artifact
        return artifact

    def status(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for version in ("v0", "W0"):
            directory = self._directory(version)
            result[version] = {
                "available": (directory / "model.joblib").exists(),
                "calibrator_available": (directory / "calibrator.joblib").exists(),
                "directory": str(directory),
            }
        return result


registry = ArtifactRegistry()
