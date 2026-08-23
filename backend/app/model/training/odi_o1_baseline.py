"""Men's ODI O1 baseline training: same estimator and calibration as frozen O0."""
from __future__ import annotations
from .odi_o0_baseline import MAX_ITER,CalibrationCandidates,O0Baseline,chronological_split,fit_validation_calibrators,predict_isotonic,predict_platt,predict_raw

def train_model_o1(X_train,y_train)->O0Baseline:
    return __import__(".odi_o0_baseline",fromlist=["train_model_o0"]).train_model_o0(X_train,y_train)
__all__=["MAX_ITER","CalibrationCandidates","O0Baseline","chronological_split","fit_validation_calibrators","predict_isotonic","predict_platt","predict_raw","train_model_o1"]
