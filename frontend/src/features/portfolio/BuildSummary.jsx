import { RefreshCw } from "lucide-react";

const sgmCorrelationBoost = (n) => n < 2 ? 1 : Math.min(1.25, 1 + 0.05 * (n - 1));

export default function BuildSummary({ legs, label, onReset, onRemove, correlated }) {
  const raw = legs.length ? legs.reduce((a, l) => a * (l.probability / 100), 1) : 0;
  const boost = correlated ? sgmCorrelationBoost(legs.length) : 1;
  const joint = Math.min(0.99, raw * boost);
  const decimal = joint > 0 ? 1 / joint : 0;
  const valid = legs.length >= 2;

  return <div className="build-summary" data-testid="build-summary">
    <div className="summary-head">
      <div><span className="eyebrow">{label} · {legs.length} LEG{legs.length === 1 ? "" : "S"}</span><div className="joint-prob" data-testid="joint-probability">{legs.length ? (joint * 100).toFixed(2) : "—"}<i>%</i></div><small>{valid ? (correlated && boost > 1 ? `Correlation-adjusted · +${((boost - 1) * 100).toFixed(0)}% SGM boost` : "Independence approximation") : "Add at least 2 legs to build a multi"}</small></div>
      <div className="summary-payout"><span className="eyebrow">IMPLIED DECIMAL</span><b data-testid="implied-decimal">{decimal ? decimal.toFixed(2) : "—"}</b><small>Analytical payout equivalent</small></div>
      {!valid && legs.length === 1 && <span className="tag amber" data-testid="need-more-legs">NEED 1 MORE LEG</span>}
      {legs.length > 0 && <button className="outline-btn" onClick={onReset} data-testid="reset-build"><RefreshCw size={14}/> RESET</button>}
    </div>
    <div className="legs-list">
      {legs.length === 0 ? <p className="legs-empty">Tap any selection above to add it as a leg</p> : legs.map((l, i) => <div className="leg-row" data-testid={`leg-${i}`} key={l.key || `${l.fixtureId || "sgm"}-${l.marketKey}-${i}`}><span className="leg-num">0{i + 1}</span><div className="leg-body"><b>{l.selectionName}</b><small>{l.marketLabel}{l.fixtureLabel ? ` · ${l.fixtureLabel}` : ""}</small></div><strong>{l.probability}%</strong><b className="leg-price">@{l.price?.toFixed(2)}</b>{onRemove && <button className="leg-remove" onClick={() => onRemove(l)} data-testid={`remove-leg-${i}`}>×</button>}</div>)}
    </div>
  </div>;
}
