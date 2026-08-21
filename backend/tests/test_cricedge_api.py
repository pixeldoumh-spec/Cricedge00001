import os
from pathlib import Path

import requests


def base_url():
    for line in Path("/app/frontend/.env").read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip().rstrip("/")
    raise AssertionError("REACT_APP_BACKEND_URL missing")


def test_fixture_feed_and_predictions():
    base = base_url()
    response = requests.get(f"{base}/api/fixtures", timeout=15)
    assert response.status_code == 200
    fixtures = response.json()
    assert len(fixtures) >= 1
    fixture = fixtures[0]
    assert fixture["teams"] and fixture["odds"] and fixture["probabilities"] if "probabilities" in fixture else fixture["odds"]
    detail = requests.get(f"{base}/api/fixtures/{fixture['id']}/predictions", timeout=15)
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["fixture"]["id"] == fixture["id"]
    assert payload["events"] and payload["same_game"]
    assert "not wagering advice" in payload["notice"].lower()


def test_portfolio_history_and_model():
    base = base_url()
    portfolio = requests.get(f"{base}/api/portfolio/predictions", timeout=15)
    history = requests.get(f"{base}/api/analytics/history", timeout=15)
    model = requests.get(f"{base}/api/analytics/model", timeout=15)
    assert portfolio.status_code == history.status_code == model.status_code == 200
    assert portfolio.json()["portfolios"]
    assert history.json()["metrics"]["accuracy"] > 0 and history.json()["series"]
    assert model.json()["version"] and model.json()["features"]


def test_unknown_fixture_is_not_found():
    response = requests.get(f"{base_url()}/api/fixtures/not-a-fixture/predictions", timeout=15)
    assert response.status_code == 404


def test_predictions_are_derived_from_each_fixture():
    base = base_url()
    fixtures = requests.get(f"{base}/api/fixtures", timeout=15).json()
    forbidden = {"Mumbai Indians", "Suryakumar Yadav", "IPL"}
    for fixture in fixtures:
        payload = requests.get(f"{base}/api/fixtures/{fixture['id']}/predictions", timeout=15).json()
        text = str(payload)
        if fixture["id"] != "f-001":
            assert not any(value in text for value in forbidden)
        assert fixture["teams"][0] in text
        assert fixture["teams"][1] in text
        assert payload["events"][1]["selection"] in payload["same_game"][0]["legs"]