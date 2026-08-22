import React from 'react';
import { ArrowUpRight, Gauge, Layers3 } from 'lucide-react';
import { fmt, formatPrice, formatProbability } from '@/lib/formatters';

export const FixtureCard = ({ fixture, onClick }) => {
  const fav = fixture.odds?.[0];
  const totalOutcomes = fixture.odds?.length || 0;

  return (
    <button
      className="fixture-card"
      data-testid={`fixture-card-${fixture.id}`}
      onClick={onClick}
    >
      <div className="card-head">
        <div>
          <span className="eyebrow">{fixture.competition} · {fixture.format}</span>
          <h3>{fixture.teams[0]} <i>vs</i> {fixture.teams[1]}</h3>
        </div>
        <span className={`tag ${fixture.model_tag === "HIGH SIGNAL" ? "red" : fixture.model_tag === "BALANCED" ? "amber" : "blue"}`}>
          {fixture.model_tag}
        </span>
      </div>
      <div className="fixture-meta">
        <span>{fmt(fixture.start_time)}</span>
        <span>{fixture.venue}</span>
        <span className="confidence">
          <Gauge size={13} /> {fixture.confidence}% confidence
        </span>
      </div>
      <div className="card-summary">
        {fav && (
          <div className="fav">
            <small>MODEL FAVOURITE</small>
            <b>{fav.name}</b>
            <span className="fav-price">{formatPrice(fav.price)} · {formatProbability(fav.probability)}</span>
          </div>
        )}
        <div className="market-count">
          <Layers3 size={13} /> {totalOutcomes} price{totalOutcomes === 1 ? "" : "s"} · 6+ markets on open
        </div>
        <div className="open-detail">
          OPEN <ArrowUpRight size={15} />
        </div>
      </div>
    </button>
  );
};
