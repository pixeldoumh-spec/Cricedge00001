import { useEffect, useState } from "react";
import MarketsBoard from "@/components/markets/MarketsBoard";
import { useFixturePredictions } from "@/hooks/useFixturePredictions";
import BuildSummary from "@/features/portfolio/BuildSummary";
import FixturePickChip from "@/features/portfolio/FixturePickChip";

function useFixtureMarkets(fixtureId) {
  const { data } = useFixturePredictions(fixtureId);
  return data?.markets || [];
}

export default function SgmBuilder({ fixtures }) {
  const [fid, setFid] = useState(() => localStorage.getItem("ce.sgm.fid") || "");
  const [legs, setLegs] = useState(() => { try { return JSON.parse(localStorage.getItem("ce.sgm.legs")) || []; } catch { return []; } });
  const markets = useFixtureMarkets(fid);

  useEffect(() => { localStorage.setItem("ce.sgm.fid", fid); }, [fid]);
  useEffect(() => { localStorage.setItem("ce.sgm.legs", JSON.stringify(legs)); }, [legs]);
  useEffect(() => { if (fid && fixtures.length && !fixtures.find(f => f.id === fid)) { setFid(""); setLegs([]); } }, [fid, fixtures]);

  const pickFixture = (id) => { if (id !== fid) { setFid(id); setLegs([]); } };
  const fixture = fixtures.find(f => f.id === fid);
  const onSelect = (market, sel) => setLegs(prev => { const existing = prev.find(l => l.marketKey === market.key); if (existing && existing.key === sel.key) return prev.filter(l => l.key !== sel.key); return [...prev.filter(l => l.marketKey !== market.key), { key: sel.key, marketKey: market.key, marketLabel: market.label, selectionName: sel.name, price: sel.price, probability: sel.probability }]; });
  const removeLeg = (leg) => setLegs(prev => prev.filter(l => l.key !== leg.key));
  const activeKeys = new Set(legs.map(l => l.key));

  return <div className="builder">
    <div className="builder-block"><div className="builder-heading"><span className="eyebrow">1 · PICK ONE FIXTURE</span><small>All SGM legs must come from this match</small></div><div className="fixture-chip-grid" data-testid="sgm-fixture-picker">{fixtures.length === 0 ? <div className="loading">No fixtures available</div> : fixtures.map(f => <FixturePickChip key={f.id} fixture={f} active={fid === f.id} onClick={() => pickFixture(f.id)} testid={`sgm-fixture-${f.id}`}/>)}</div></div>
    {fid && fixture && <div className="builder-block"><div className="builder-heading"><span className="eyebrow">2 · BUILD YOUR LEGS · {legs.length} SELECTED</span><small>{fixture.teams[0]} vs {fixture.teams[1]} · {markets.length} markets · one selection per market</small></div>{markets.length === 0 ? <div className="loading">Loading markets…</div> : <MarketsBoard markets={markets} activeKeys={activeKeys} onSelect={onSelect}/>}</div>}
    <BuildSummary legs={legs} label="SAME-GAME MULTI" onReset={() => setLegs([])} onRemove={removeLeg} correlated={true}/>
  </div>;
}
