from typing import List, Optional

from pydantic import BaseModel


class Outcome(BaseModel):
    name: str
    price: float
    probability: float
    edge: float


class Fixture(BaseModel):
    id: str
    competition: str
    format: str
    venue: str
    start_time: str
    teams: List[str]
    status: str
    model_tag: str
    confidence: int
    odds: List[Outcome]
    live_totals: Optional[dict] = None
    sample: bool = True
    data_quality: str = "LOW"
    model_win: Optional[dict] = None
    model_note: Optional[str] = None
