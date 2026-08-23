# ODI Experiment Lineage Reconciliation

Date: 2026-08-23

## Purpose

Reconcile the provenance of O12 and the diagnostic chain that led to O14 before any O15 hypothesis is considered.

## 1. Canonical corpus and recovery

The recovery manifest identifies `Cricedge00001` as the canonical ODI repository, records the locked corpus SHA-256 as `f0798ef14e1f3f61720d41978289fe7318257263f59edba5dca0b35dbba64d6c`, and records 2,440 decisive matches. It also records the recovered O0-O12 implementation chain and explicitly states that O0 remains frozen.

## 2. O12 provenance

O12 is not merely an informal chat hypothesis. The repository contains:

- an O12 controlled-change contract;
- an O12 feature implementation;
- O12 unit tests;
- an O12 evaluation report;
- an O12 decision record.

The O12 contract states the exact hypothesis as `strength_difference * log1p(min_pre_match_decisive_history)`, requires pre-match history only, preserves O0, forbids test-period fitting/tuning, and specifies the chronological O0 split, rolling-origin evaluation, and future holdout.

The O12 implementation adds exactly one feature to the frozen O0 dictionary and derives its history context from the minimum of the two teams' pre-match decisive-history counts. The unit tests explicitly check the minimum-history rule, negative-history rejection, O0 preservation, zero-history behavior, and absence of outcome/innings inputs.

The committed O12 evaluation report states that the locked population is 2,569 JSON matches / 2,440 decisive matches and that the untouched test was not used for tuning. It reports O12 losing the untouched test on log loss, Brier, AUC, and ECE, and the independent future holdout exposing a severe failure for validation-selected calibrated O12. The decision is to reject O12 and keep O0 frozen.

### Reconciliation finding

The repository evidence supports treating O12 as a **documented completed controlled experiment**. An earlier handoff statement claiming that O12 had not legitimately been completed is inconsistent with the current recovered repository record. That statement must therefore be treated as superseded provenance commentary, not as the authoritative experiment status.

However, the O12 evaluation report is a stored result artifact. The current public repository does not expose, in the files inspected for this audit, a single self-contained O12 evaluation runner that reproduces every reported numerical field end-to-end. Therefore the O12 result is **repository-recorded evidence**, not independently re-executed evidence in this reconciliation pass.

We must not describe it as independently rerun here.

## 3. Diagnostic lineage from O12 to O14

The O12 decision explicitly required diagnostic separation of four causes before proposing the next hypothesis: calibration, strength representation, matchup/context asymmetry, and temporal distribution shift.

The repository subsequently records:

1. D1-D3 temporal/calibration/context diagnostics.
2. T1 temporal relationship diagnostic.
3. D4 score-to-probability mapping diagnostic.
4. D5 chronological adaptive-calibration diagnostic.
5. Conditional coefficient-drift diagnostic.
6. Symmetric signed-drift diagnostic.
7. O14 hypothesis/evaluation contract.

The conditional coefficient diagnostic identifies three candidate components with reproducible temporal coefficient drift across five expanding chronological prefixes: recent win-rate, runs-conceded-per-ball, and defend-win-rate, initially observed in positional Team-B features.

The symmetric signed diagnostic then converts these to semantic A-minus-B representations and reports that all three retain consistent coefficient-drift direction with bootstrap intervals excluding zero, while the other signed components do not meet the same reproducibility rule. This is the direct provenance basis for O14.

## 4. O14 hypothesis provenance

O14 was not chosen from the untouched test or future holdout. Its frozen contract explicitly says:

- exactly three validated symmetric signed components;
- chronological interaction only;
- training-prefix-only time normalization;
- no uniform half-life decay;
- no history-depth interaction;
- no other O0 time interactions;
- no additional match-level features;
- no post-hoc test tuning;
- no future-holdout-driven selection.

The O14 contract therefore follows the diagnostic chain rather than replacing it with a new arbitrary transformation.

## 5. Important provenance limitation

The diagnostic JSON artifacts contain numerical results and methodology descriptions, but this audit did not independently reproduce every diagnostic statistic from raw corpus bytes. Consequently, the correct provenance language is:

> O14 is **supported by the committed diagnostic evidence chain**, with its immediate hypothesis selection traceable to the conditional coefficient and symmetric signed diagnostics.

It is not correct to claim that every preceding diagnostic statistic has been independently re-executed in this reconciliation pass.

## 6. O14 execution status

O14 was subsequently executed under its frozen protocol. Its recorded result does not justify promotion: it did not produce a robust primary-metric improvement that survived the independent future holdout. O0 therefore remains the control.

The O14 outcome must not be used to retroactively modify the O14 hypothesis.

## 7. Final lineage decision

The reconciled chain is:

`Recovery → O0 frozen → O12 documented controlled experiment → O12 rejected → diagnostic-only analysis → conditional coefficient drift → symmetric signed validation → O14 frozen → O14 executed → O14 rejected → O0 remains frozen.`

There is **no methodological basis to invent O15 yet**.

Before any new hypothesis, the next work should be a provenance-quality improvement: preserve executable evaluation runners/artifact manifests for every diagnostic and experiment so that future decisions can be reproduced from the locked corpus without relying on narrative result files alone.
