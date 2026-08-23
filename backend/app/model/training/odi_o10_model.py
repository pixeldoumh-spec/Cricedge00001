"""ODI O10 controlled LogisticRegression regularization sweep."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence,Tuple
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
CANDIDATE_C=(0.25,0.5,1.0,2.0,4.0);CONTROL_C=1.0;MAX_ITER=2000
@dataclass
class O10Model: scaler:StandardScaler;model:LogisticRegression;C:float
@dataclass
class O10Calibrators: platt:LogisticRegression; isotonic:IsotonicRegression
def fit_o10(X_train,y_train,C):
 if X_train.ndim!=2 or X_train.shape[1]!=13:raise ValueError("O10 requires the exact frozen O0 13-feature matrix")
 if C not in CANDIDATE_C:raise ValueError("O10 C must be one of the frozen contract candidates")
 scaler=StandardScaler();model=LogisticRegression(max_iter=MAX_ITER,C=float(C));model.fit(scaler.fit_transform(X_train),y_train);return O10Model(scaler,model,float(C))
def predict_raw(bundle,X):return bundle.model.predict_proba(bundle.scaler.transform(X))[:,1]
def select_C_by_validation_log_loss(X_train,y_train,X_validation,y_validation):
 from sklearn.metrics import log_loss
 scores=[]
 for C in CANDIDATE_C:
  b=fit_o10(X_train,y_train,C);scores.append((float(log_loss(y_validation,predict_raw(b,X_validation),labels=[0,1])),C))
 best_loss,best_C=min(scores,key=lambda x:(x[0],x[1]));return float(best_C),scores
def fit_validation_calibrators(raw_validation,y_validation):
 p=np.asarray(raw_validation,float);y=np.asarray(y_validation,int);platt=LogisticRegression(max_iter=MAX_ITER);platt.fit(p.reshape(-1,1),y);iso=IsotonicRegression(out_of_bounds="clip");iso.fit(p,y);return O10Calibrators(platt,iso)
def predict_platt(calibrator,probabilities):return calibrator.predict_proba(np.asarray(probabilities).reshape(-1,1))[:,1]
def predict_isotonic(calibrator,probabilities):return calibrator.predict(np.asarray(probabilities,dtype=float))
