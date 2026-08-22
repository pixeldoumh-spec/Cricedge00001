# Women's W0 production reference

W0 is the frozen women's T20 reference implementation. It is **not** a promoted calibrated production model: the final holdout showed that validation Platt calibration did not improve the final holdout consistently.

Production loading therefore uses `model.joblib` only for W0. Do not add `calibrator.joblib` to the W0 deployment artifact until a new calibration decision is evaluated and explicitly promoted.

Deployment artifact is generated outside GitHub from the retained corpus and exact training code. Commit source metadata/checksums, not the binary model files.
