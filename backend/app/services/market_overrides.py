import cric_model


def _ou(key: str, label_line: float, mean: float, sd: float) -> dict:
    """Build a model-derived over/under market payload from a normal approximation."""
    over = cric_model.norm_sf(label_line, mean, sd)
    under = 1 - over
    return {
        "line": f"O/U {label_line}",
        "selections": [
            {"key": f"{key}_over", "name": f"Over {label_line}", "price": round(1 / over, 2), "probability": round(over * 100)},
            {"key": f"{key}_under", "name": f"Under {label_line}", "price": round(1 / under, 2), "probability": round(under * 100)},
        ],
    }


def _line_for(mean: float, step: int) -> float:
    return round(mean / step) * step + 0.5


def model_overrides(prediction: dict, home: str, away: str, fmt: str) -> dict:
    """Map the trained model output onto sportsbook market keys."""
    teams = prediction.get("teams") or {}
    h = teams.get("home") or {}
    a = teams.get("away") or {}
    out: dict[str, dict] = {}
    if not h or not a:
        return out
    step = 5 if fmt in ("T20", "Hundred") else 10
