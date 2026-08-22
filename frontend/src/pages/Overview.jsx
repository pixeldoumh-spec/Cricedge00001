import { Activity, Database, Gauge, RefreshCw, ShieldCheck, TrendingUp } from "lucide-react";
import { useState } from "react";
import { useFixtureFormats, useFixtures } from "@/hooks/useFixtures";
import Shell from "@/components/layout/Shell";
import Metric from "@/components/layout/Metric";
import FixtureCard from "@/components/fixtures/FixtureCard";
import FormatFilter from "@/components/fixtures/FormatFilter";

const getApiErrorMessage = (error, fallback) => error?.userMessage || error?.response?.data?.detail || fallback;

export default function Overview() {
  const [active, setActive] = useState("ALL");
  const { data: fixtures = [], isLoading: fixturesLoading, error: fixturesError, refetch: refetchFixtures } = useFixtures(active);
  const { data: formatData = { formats: [], total: 0 }, isLoading: formatsLoading, error: formatsError, refetch: refetchFormats } = useFixtureFormats();
  const formats = formatData.formats || [];
  const total = formatData.total || 0;
  const loading = fixturesLoading || formatsLoading;
  const error = fixturesError ? getApiErrorMessage(fixturesError, "Fixture feed unavailable") : formatsError ? getApiErrorMessage(formatsError, "Format data unavailable") : "";
  const refresh = () => { refetchFixtures(); refetchFormats(); };
  return <Shell><div className="page">
    <div className="page-intro"><div><div className="eyebrow accent">MATCH CENTER / 06:42 UTC</div><h1>Fixture explorer</h1><p>Signals, prices, and context for the global cricket slate.</p></div><button data-testid="refresh-fixtures-button" className="outline-btn" onClick={refresh} disabled={loading}><RefreshCw size={15}/> {loading ? "REFRESHING…" : "REFRESH FEED"}</button></div>
    <div className="disclaimer" data-testid="analytics-disclaimer"><ShieldCheck size={17}/><span><b>ANALYTICAL SIGNALS ONLY</b> CricEdge publishes model outputs for research and education. This is not wagering advice and contains no stake sizing.</span></div>
    <div className="metrics"><Metric label="Upcoming fixtures" value={total || "—"} delta="Live provider feed" icon={Activity}/><Metric label="Model coverage" value="92.6%" delta="+1.4% this week" icon={Database}/><Metric label="Mean confidence" value="68.4%" delta="+3.2% vs baseline" icon={TrendingUp}/><Metric label="Pipeline status" value="NOMINAL" delta="Updated 2m ago" icon={Gauge}/></div>
    <FormatFilter formats={formats} active={active} total={total} onChange={setActive}/>
    <div className="section-heading"><div><span className="eyebrow">UPCOMING SLATE · {active === "ALL" ? "ALL FORMATS" : active.toUpperCase()}</span><h2>Next fixtures</h2></div><span className="count" data-testid="fixture-count">{loading ? "—" : `${fixtures.length} LOADED`}</span></div>
    {error && <div className="error" data-testid="fixture-error">{error}</div>}
    <div className="fixture-list">{loading ? <div className="loading" data-testid="fixtures-loading">Loading normalized fixtures…</div> : fixtures.length === 0 ? <div className="loading" data-testid="fixtures-empty">No fixtures for this format right now.</div> : fixtures.map((fixture) => <FixtureCard fixture={fixture} key={fixture.id}/>)}</div>
  </div></Shell>;
}
