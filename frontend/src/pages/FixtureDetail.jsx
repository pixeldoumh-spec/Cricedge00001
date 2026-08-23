import { ArrowUpRight, ShieldCheck } from "lucide-react";
import { NavLink, useParams } from "react-router-dom";
import { useFixturePredictions } from "@/hooks/useFixturePredictions";
import Shell from "@/components/layout/Shell";
import MarketsBoard from "@/components/markets/MarketsBoard";

const fmt = (value) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Start time unavailable" : date.toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" });
};
const getApiErrorMessage = (error, fallback) => error?.userMessage || error?.response?.data?.detail || error?.message || fallback;

export default function FixtureDetail() {
  const { id } = useParams();
  const { data, isLoading, error } = useFixturePredictions(id);
  if (isLoading) return <Shell><div className="loading">Loading fixture markets…</div></Shell>;
  if (error) return <Shell><div className="loading error" data-testid="fixture-detail-error">{getApiErrorMessage(error, "Unable to load this fixture. Please try again.")}</div></Shell>;
  if (!data?.fixture) return <Shell><div className="loading error" data-testid="fixture-detail-error">Fixture data is unavailable.</div></Shell>;

  const fixture = data.fixture;
  const teams = Array.isArray(fixture.teams) ? fixture.teams : [];
  const home = teams[0] || "Home";
  const away = teams[1] || "Away";

  return <Shell><div className="page">
    <NavLink className="back" to="/" data-testid="back-fixtures-link">← ALL FIXTURES</NavLink>
    <div className="page-intro">
      <div><div className="eyebrow accent">FIXTURE DETAIL / {fixture.format || "T20"}</div><h1>{home} <em>vs</em> {away}</h1><p>{fixture.competition || "Cricket"} · {fixture.venue || "Venue unavailable"} · {fmt(fixture.start_time)}</p></div>
      <span className="tag red">{Number.isFinite(Number(fixture.confidence)) ? `${fixture.confidence}% MODEL CONFIDENCE` : "MODEL CONFIDENCE UNAVAILABLE"}</span>
    </div>
    <div className="disclaimer" data-testid="detail-disclaimer"><ShieldCheck size={17}/><span>{data.notice || "Model probabilities are predictive estimates, not wagering advice."}</span></div>
    <div className="strategy-banner" data-testid="strategy-banner"><span className="strategy-tag">{fixture.format || "T20"}</span><div><span className="eyebrow">FORMAT STRATEGY</span><b>{data.strategy === "model_artifact" ? "Model artifact prediction" : "Catalogue baseline"}</b></div><small>{data.markets.length} markets · click any selection to open the builder</small></div>
    <div className="detail-cta"><div><span className="eyebrow">READY TO COMBINE?</span><b>Build a Same-Game Multi from these markets</b></div><NavLink to="/portfolio" className="outline-btn" data-testid="open-builder-link" onClick={() => { localStorage.setItem("ce.portfolio.mode", "SGM"); localStorage.setItem("ce.sgm.fid", fixture.id); localStorage.setItem("ce.sgm.legs", "[]"); }}>OPEN BUILDER <ArrowUpRight size={14}/></NavLink></div>
    <MarketsBoard markets={data.markets} activeKeys={new Set()} filter={null}/>
  </div></Shell>;
}
