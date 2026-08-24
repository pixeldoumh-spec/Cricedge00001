"""Normalize Cricsheet JSON into a stable internal match representation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class NormalizedPlayer:
    name: str
    registry_id: str | None = None


@dataclass(frozen=True)
class NormalizedDelivery:
    innings: int
    batting_team: str
    bowling_team: str
    over: int
    ball: int
    batter: str
    bowler: str
    non_striker: str
    batter_runs: int
    extras: int
    total_runs: int
    wicket: bool = False
    wides: int = 0
    no_balls: int = 0
    byes: int = 0
    leg_byes: int = 0
    penalty_runs: int = 0

    @property
    def legal_ball(self) -> bool:
        """Whether this delivery consumes a legal ball under T20 scoring rules."""
        return self.wides == 0 and self.no_balls == 0


@dataclass(frozen=True)
class CanonicalMatch:
    match_id: str
    dates: tuple[str, ...]
    teams: tuple[str, ...]
    venue: str | None
    city: str | None
    season: str | int | None
    competition: str | None
    gender: str | None
    match_type: str | None
    team_type: str | None
    toss_winner: str | None
    toss_decision: str | None
    winner: str | None
    result_type: str | None
    players: dict[str, tuple[NormalizedPlayer, ...]] = field(default_factory=dict)
    deliveries: tuple[NormalizedDelivery, ...] = ()


def _first(value: Any) -> str | None:
    if isinstance(value, list) and value:
        return str(value[0])
    if value is None:
        return None
    return str(value)


def normalize_match(match_id: str, raw: dict[str, Any]) -> CanonicalMatch:
    """Convert one Cricsheet JSON match into our canonical representation."""
    info = raw.get("info") or {}
    teams = tuple(str(team) for team in (info.get("teams") or []))
    toss = info.get("toss") or {}
    outcome = info.get("outcome") or {}
    winner = outcome.get("winner")
    result_type = next((key for key in ("winner", "result", "eliminator") if key in outcome), None)

    event = info.get("event") or {}
    competition = event.get("name") if isinstance(event, dict) else None

    players: dict[str, tuple[NormalizedPlayer, ...]] = {}
    registry = info.get("registry") or {}
    people_registry = registry.get("people") or {}
    for team, names in (info.get("players") or {}).items():
        players[str(team)] = tuple(
            NormalizedPlayer(name=str(name), registry_id=people_registry.get(name))
            for name in names
        )

    deliveries: list[NormalizedDelivery] = []
    for innings_index, innings in enumerate(raw.get("innings") or [], start=1):
        batting_team = str(innings.get("team", ""))
        bowling_team = next((team for team in teams if team != batting_team), "")
        for over in innings.get("overs") or []:
            over_number = int(over.get("over", 0))
            for ball_index, delivery in enumerate(over.get("deliveries") or []):
                runs = delivery.get("runs") or {}
                extras = delivery.get("extras") or {}
                deliveries.append(
                    NormalizedDelivery(
                        innings=innings_index,
                        batting_team=batting_team,
                        bowling_team=bowling_team,
                        over=over_number,
                        ball=ball_index,
                        batter=str(delivery.get("batter", "")),
                        bowler=str(delivery.get("bowler", "")),
                        non_striker=str(delivery.get("non_striker", "")),
                        batter_runs=int(runs.get("batter", 0)),
                        extras=int(sum(extras.values())) if extras else 0,
                        total_runs=int(runs.get("total", 0)),
                        wicket=bool(delivery.get("wickets")),
                        wides=int(extras.get("wides", 0)),
                        no_balls=int(extras.get("noballs", 0)),
                        byes=int(extras.get("byes", 0)),
                        leg_byes=int(extras.get("legbyes", 0)),
                        penalty_runs=int(extras.get("penalty", 0)),
                    )
                )

    return CanonicalMatch(
        match_id=match_id,
        dates=tuple(str(d) for d in (info.get("dates") or [])),
        teams=teams,
        venue=info.get("venue"),
        city=info.get("city"),
        season=info.get("season"),
        competition=competition,
        gender=info.get("gender"),
        match_type=info.get("match_type"),
        team_type=info.get("team_type"),
        toss_winner=toss.get("winner"),
        toss_decision=toss.get("decision"),
        winner=winner,
        result_type=result_type,
        players=players,
        deliveries=tuple(deliveries),
    )
