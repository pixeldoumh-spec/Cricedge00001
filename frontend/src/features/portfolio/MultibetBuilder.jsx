import { useEffect, useState } from "react";
import MarketsBoard from "@/components/markets/MarketsBoard";
import { useFixturePredictions } from "@/hooks/useFixturePredictions";
import BuildSummary from "@/features/portfolio/BuildSummary";
import FixturePickChip from "@/features/portfolio/FixturePickChip";

function MultibetLegPicker({ fixture, pick, onSelect, idx }) {
  const { data } = useFixturePredictions(fixture.id);
  const markets = data?.markets || [];
  const activeKeys = new Set(pick?.key ? [pick.key] : []);
  return <div className="leg-picker" data-testid={`multi-leg-picker-${idx}`}><div className="leg-picker-head"><span className="eyebrow">LEG 0{idx + 1} · {fixture.format} · one selection only</span><b>{fixture.teams[0]} <i>vs</i> {fixture.teams[1]}</b></div>{markets.length === 0 ? <div className="loading">Loading…</div> : <MarketsBoard markets={markets} activeKeys={activeKeys} onSelect={(market, sel) => onSelect(fixture.id, market, sel)}/>}</div>;
}

export default function MultibetBuilder({ fixtures }) {
  const [picks, setPicks] = useState(() => { try { return JSON.parse(localStorage.getItem("ce.multi.picks")) || []; } catch { return []; } });
  useEffect(() => { localStorage.setItem("ce.multi.picks", JSON.stringify(picks)); }, [picks]);
  useEffect(() => { if (fixtures.length) setPicks(prev => prev.filter(p => fixtures.find(f => f.id === p.fixtureId))); }, [fixtures]);

  const selectedIds = picks.map(p => p.fixtureId);
  const canAdd = selectedIds.length < 10;
  const toggleFixture = (fid) => { if (selectedIds.includes(fid)) setPicks(prev => prev.filter(p => p.fixtureId !== fid)); else if (canAdd) setPicks(prev => [...prev, { fixtureId: fid, key: null, marketKey: null, marketLabel: null, selectionName: null, price: null, probability: null }]); };
  const onSelect = (fid, market, sel) => setPicks(prev => prev.map(p => { if (p.fixtureId !== fid) return p; if (p.key === sel.key) return { ...p, key: null, marketKey: null, marketLabel: null, selectionName: null, price: null, probability: null }; return { ...p, key: sel.key, marketKey: market.key, marketLabel: market.label, selectionName: sel.name, price: sel.price, probability: sel.probability }; }));
  const removeLeg = (leg) => setPicks(prev => prev.filter(p => p.key !== leg.key));
  const legs = picks.filter(p => p.key != null).map(p => { const f = fixtures.find(fx => fx.id === p.fixtureId); return { ...p, fixtureLabel: f ? `${f.teams[0]} vs ${f.teams[1]}` : "" }; });

  return <div className="builder">
    <div className="builder-block"><div className="builder-heading"><span className="eyebrow">1 · PICK UP TO 10 FIXTURES · {picks.length}/10</span><small>Cross-format allowed · exactly one selection per fixture</small></div><div className="fixture-chip-grid" data-testid="multi-fixture-picker">{fixtures.length === 0 ? <div className="loading">No fixtures available</div> : fixtures.map(f => { const isSelected = selectedIds.includes(f.id); return <FixturePickChip key={f.id} fixture={f} active={isSelected} disabled={!isSelected && !canAdd} onClick={() => toggleFixture(f.id)} testid={`multi-fixture-${f.id}`}/>; })}</div></div>
    {picks.length > 0 && <div className="builder-block"><div className="builder-heading"><span className="eyebrow">2 · PICK ONE SELECTION PER LEG</span><small>{legs.length}/{picks.length} legs set</small></div><div className="legs-picker-stack">{picks.map((pick, idx) => { const fixture = fixtures.find(f => f.id === pick.fixtureId); return fixture ? <MultibetLegPicker key={pick.fixtureId} fixture={fixture} pick={pick} onSelect={onSelect} idx={idx}/> : null; })}</div></div>}
    <BuildSummary legs={legs} label="MULTIBET" onReset={() => setPicks([])} onRemove={removeLeg} correlated={false}/>
  </div>;
}
