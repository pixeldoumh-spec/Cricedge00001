"""ODI O4: nonlinear estimator on the exact frozen O0 13-feature matrix."""
from __future__ import annotations
from dataclasses import dataclass
from sklearn.ensemble import HistGradientBoostingClassifier
@dataclass
class O4Model: model: HistGradientBoostingClassifier
def train_model_o4(X_train,y_train)->O4Model:
    model=HistGradientBoostingClassifier(learning_rate=0.05,max_iter=200,max_leaf_nodes=7,min_samples_leaf=20,l2_regularization=1.0,random_state=0); model.fit(X_train,y_train); return O4Model(model=model)
def predict_raw(model:O4Model,X): return model.model.predict_proba(X)[:,1]
