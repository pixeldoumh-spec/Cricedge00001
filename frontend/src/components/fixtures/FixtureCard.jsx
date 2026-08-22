import { useNavigate } from "react-router-dom";
import { ArrowUpRight, Gauge, Layers3 } from "lucide-react";

const fmt = (value) => new Date(value).toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" });

export default function FixtureCard({ fixture }) {
  const navigate = useNavigate();
  const odds = Array.isArray(fixture?.odds) ? fixture.odds : [];
  const fav = odds[0];

  return (
    <button className="fixture-card" data-testid={`fixture-card-${fixture.id}`} onClick={() => navigate(`/fixture/${fixture.id}`)}>
      <div className="card-head">
        <div>
          <span className="eyebrow">{fixture.competition} · {fixture.format}</span>
          <h3>{fixture.teams[0]} <i>vs</i> {fixture.teams[1]}</h3>
        </div>
        <span className={`tag ${fixture.model_tag === "HIGH SIGNAL" ? "red" : fixture.model_tag === "BALANCED" ? "amber" : "blue"}`}>{fixture.model_tag}</span>
      </div>
      <div className="fixture-meta">
        <span>{fmt(fixture.start_time)}</span>
        <span>{fixture.venue}</span>
        <span className="confidence"><Gauge size={13}/> {fixture.confidence}% confidence</span>
      </div>
      <div className="card-summary">
        {fav && <div className="fav"><small>MODEL FAVOURITE</small><b>{fav.name}</b><span className="fav-price">{fav.price.toFixed(2)} · {Math.round(fav.probability * 100)}%</span></div>}
        <div className="market-count"><Layers3 size={13}/> {odds.length} price{odds.length === 1 ? "" : "s"} · 6+ markets on open</div>
        <div className="open-detail">OPEN <ArrowUpRight size={15}/></div>
      </div>
    </button>
  );
}
