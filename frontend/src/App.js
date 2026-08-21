import { useEffect, useState } from "react";
import axios from "axios";
import { BrowserRouter, NavLink, Routes, Route, useNavigate, useParams } from "react-router-dom";
import { AreaChart, Area, ResponsiveContainer, XAxis, YAxis, Tooltip, BarChart, Bar } from "recharts";
import { Activity, ArrowUpRight, BarChart3, ChevronRight, CircleHelp, Database, Gauge, Layers3, RefreshCw, ShieldCheck, Target, TrendingUp } from "lucide-react";
import "@/App.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const fmt = (value) => new Date(value).toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" });
const nav = [{to:"/", label:"Fixtures", icon:Activity}, {to:"/portfolio", label:"Portfolios", icon:Layers3}, {to:"/history", label:"Performance", icon:BarChart3}, {to:"/model", label:"Model insight", icon:Target}];

function Shell({children}) { return <div className="app-shell"><aside><div className="brand"><span className="brand-mark">CE</span><span>Cric<span>Edge</span><small>ANALYTICS ENGINE</small></span></div><div className="nav-label">WORKSPACE</div><nav>{nav.map(({to,label,icon:Icon})=><NavLink data-testid={`nav-${label.toLowerCase().replace(' ','-')}`} key={to} to={to} end={to==="/"}><Icon size={17}/>{label}<ChevronRight className="nav-arrow" size={14}/></NavLink>)}</nav><div className="side-status"><div className="live-dot"/> DATA PIPELINE <strong>OPERATIONAL</strong><p>Last normalized<br/><b>2 min ago</b></p></div><div className="side-footer"><ShieldCheck size={15}/> Read-only environment<br/><span>v0.8.2 · UTC</span></div></aside><main><header className="topbar"><div className="crumb"><span>CRICEDGE</span><ChevronRight size={14}/><b>ANALYTICS</b></div><div className="top-actions"><span className="sync"><span className="live-dot"/> LIVE FEED</span><button data-testid="help-button" className="icon-btn" title="Help"><CircleHelp size={18}/></button><div className="avatar">CE</div></div></header>{children}</main></div> }

function Metric({label,value,delta,icon:Icon}) { return <div className="metric" data-testid={`metric-${label.toLowerCase().replaceAll(' ','-')}`}><div className="metric-top"><span>{label}</span><Icon size={16}/></div><b>{value}</b><small className={delta?.startsWith("+")?"up":""}>{delta}</small></div> }
function FixtureCard({fixture}) {
  const navigate=useNavigate();
  const fav = fixture.odds[0];
  const totalOutcomes = fixture.odds.length;
  return <button className="fixture-card" data-testid={`fixture-card-${fixture.id}`} onClick={()=>navigate(`/fixture/${fixture.id}`)}>
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
      {fav && <div className="fav">
        <small>MODEL FAVOURITE</small>
        <b>{fav.name}</b>
        <span className="fav-price">{fav.price.toFixed(2)} · {Math.round(fav.probability*100)}%</span>
      </div>}
      <div className="market-count"><Layers3 size={13}/> {totalOutcomes} price{totalOutcomes===1?"":"s"} · 6+ markets on open</div>
      <div className="open-detail">OPEN <ArrowUpRight size={15}/></div>
    </div>
  </button>
}
function FormatFilter({formats,active,onChange,total}) {
  const chips = [{key:"ALL", label:"All formats", count: total, profile:"Full cricket slate"}, ...formats.map(f=>({key:f.key, label:f.label, count:f.count, profile:f.profile}))];
  return <div className="format-filter" data-testid="format-filter">
    <div className="filter-label"><span className="eyebrow">FORMAT STRATEGY</span><small>Predictions adapt to each format</small></div>
    <div className="chip-row">{chips.map(c=><button key={c.key} data-testid={`format-chip-${c.key.toLowerCase()}`} className={`chip ${active===c.key?"active":""} ${c.count===0&&c.key!=="ALL"?"empty":""}`} onClick={()=>onChange(c.key)} disabled={c.count===0&&c.key!=="ALL"} title={c.profile}><span>{c.label}</span><b>{c.count}</b></button>)}</div>
  </div>
}
function Overview() {
  const [fixtures,setFixtures]=useState([]);
  const [formats,setFormats]=useState([]);
  const [total,setTotal]=useState(0);
  const [active,setActive]=useState("ALL");
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  useEffect(()=>{
    axios.get(`${API}/fixtures/formats`).then(r=>{setFormats(r.data.formats);setTotal(r.data.total)}).catch(()=>{});
  },[]);
  useEffect(()=>{
    setLoading(true); setError("");
    const params = active==="ALL" ? {} : {params:{format:active}};
    axios.get(`${API}/fixtures`, params).then(r=>setFixtures(r.data)).catch(()=>setError("Fixture feed unavailable")).finally(()=>setLoading(false));
  },[active]);
  return <Shell><div className="page"><div className="page-intro"><div><div className="eyebrow accent">MATCH CENTER / 06:42 UTC</div><h1>Fixture explorer</h1><p>Signals, prices, and context for the global cricket slate.</p></div><button data-testid="refresh-fixtures-button" className="outline-btn" onClick={()=>window.location.reload()}><RefreshCw size={15}/> REFRESH FEED</button></div><div className="disclaimer" data-testid="analytics-disclaimer"><ShieldCheck size={17}/><span><b>ANALYTICAL SIGNALS ONLY</b> CricEdge publishes model outputs for research and education. This is not wagering advice and contains no stake sizing.</span></div><div className="metrics"><Metric label="Upcoming fixtures" value={total||"—"} delta="Live provider feed" icon={Activity}/><Metric label="Model coverage" value="92.6%" delta="+1.4% this week" icon={Database}/><Metric label="Mean confidence" value="68.4%" delta="+3.2% vs baseline" icon={TrendingUp}/><Metric label="Pipeline status" value="NOMINAL" delta="Updated 2m ago" icon={Gauge}/></div>
    <FormatFilter formats={formats} active={active} total={total} onChange={setActive}/>
    <div className="section-heading"><div><span className="eyebrow">UPCOMING SLATE · {active==="ALL"?"ALL FORMATS":active.toUpperCase()}</span><h2>Next fixtures</h2></div><span className="count" data-testid="fixture-count">{loading?"—":`${fixtures.length} LOADED`}</span></div>{error&&<div className="error" data-testid="fixture-error">{error}</div>}<div className="fixture-list">{loading ? <div className="loading" data-testid="fixtures-loading">Loading normalized fixtures…</div> : fixtures.length===0 ? <div className="loading" data-testid="fixtures-empty">No fixtures for this format right now.</div> : fixtures.map(f=><FixtureCard fixture={f} key={f.id}/>)}</div><div className="lower-grid"><div className="callout"><div className="callout-icon"><Database size={19}/></div><div><b>Source health</b><p>Cricsheet history normalized · bookmaker adapter ready</p></div><span className="healthy">● HEALTHY</span></div><div className="callout"><div className="callout-icon blue-icon"><Target size={19}/></div><div><b>Model registry</b><p>Ensemble v0.8.2 · retrained 14 Jun 2025</p></div><NavLink to="/model" data-testid="view-model-link">VIEW MODEL <ArrowUpRight size={14}/></NavLink></div></div></div></Shell>
}
function Detail() { const {id}=useParams(); const [data,setData]=useState(null); useEffect(()=>{axios.get(`${API}/fixtures/${id}/predictions`).then(r=>setData(r.data))},[id]); if(!data)return <Shell><div className="loading">Loading model detail…</div></Shell>; return <Shell><div className="page"><NavLink className="back" to="/" data-testid="back-fixtures-link">← ALL FIXTURES</NavLink><div className="page-intro"><div><div className="eyebrow accent">FIXTURE DETAIL / {data.fixture.format}</div><h1>{data.fixture.teams[0]} <em>vs</em> {data.fixture.teams[1]}</h1><p>{data.fixture.competition} · {data.fixture.venue} · {fmt(data.fixture.start_time)}</p></div><span className="tag red">{data.fixture.confidence}% MODEL CONFIDENCE</span></div><div className="disclaimer" data-testid="detail-disclaimer"><ShieldCheck size={17}/><span>{data.notice}</span></div>{data.strategy&&<div className="strategy-banner" data-testid="strategy-banner"><span className="strategy-tag">{data.strategy.format}</span><div><span className="eyebrow">FORMAT STRATEGY</span><b>{data.strategy.profile}</b></div><small>Predictions and multis are calibrated to this format's baseline priors.</small></div>}<div className="detail-grid"><section className="panel"><div className="panel-title"><div><span className="eyebrow">EVENT PROBABILITIES</span><h2>Model signals</h2></div><span className="mono">ENSEMBLE / V0.8.2</span></div>{data.events.map((e,i)=><div className="signal" data-testid={`prediction-event-${i}`} key={e.market}><div className="signal-main"><span className="signal-num">0{i+1}</span><div><b>{e.selection}</b><small>{e.market} · {e.confidence} confidence</small>{e.drivers&&<div className="drivers">{e.drivers.map(d=><span key={d}>{d}</span>)}</div>}</div></div><div className="prob"><strong>{e.probability}%</strong><div className="bar"><i style={{width:`${e.probability}%`}}/></div></div></div>)}</section><section className="panel" data-testid="odds-board"><div className="panel-title"><div><span className="eyebrow">MATCH ODDS BOARD</span><h2>Live prices</h2></div><span className="mono">MEDIAN OF BOOKMAKERS</span></div>{data.fixture.odds.length===0 ? <div className="loading">Odds pending</div> : data.fixture.odds.map((o,i)=><div className="odds-row-item" data-testid={`odds-row-${i}`} key={o.name}><div><b>{o.name}</b><small>Implied {Math.round(o.probability*100)}%</small></div><strong>{o.price.toFixed(2)}</strong></div>)}<div className="panel-title" style={{marginTop:24}}><div><span className="eyebrow">SAME-GAME MULTIS</span><h2>Combination engine</h2></div></div>{data.same_game.map((m,i)=><div className="multi" data-testid={`same-game-multi-${i}`} key={m.label}><div><b>{m.label}</b>{m.legs.map(l=><span key={l}>+ {l}</span>)}</div><strong>{m.probability}%<small>JOINT PROB.</small></strong></div>)}</section></div></div></Shell> }
function useFixtureEvents(fixtureId) {
  const [events, setEvents] = useState([]);
  useEffect(() => {
    if (!fixtureId) { setEvents([]); return; }
    axios.get(`${API}/fixtures/${fixtureId}/predictions`).then(r => setEvents(r.data.events)).catch(()=>setEvents([]));
  }, [fixtureId]);
  return events;
}
function BuildSummary({legs, label, onReset}) {
  const joint = legs.length ? legs.reduce((a,l)=>a*(l.probability/100), 1) : 0;
  const decimal = joint > 0 ? (1/joint) : 0;
  return <div className="build-summary" data-testid="build-summary">
    <div className="summary-head">
      <div>
        <span className="eyebrow">{label} · {legs.length} LEG{legs.length===1?"":"S"}</span>
        <div className="joint-prob" data-testid="joint-probability">{legs.length ? (joint*100).toFixed(2) : "—"}<i>%</i></div>
        <small>Joint probability · independence approximation</small>
      </div>
      <div className="summary-payout">
        <span className="eyebrow">IMPLIED DECIMAL</span>
        <b data-testid="implied-decimal">{decimal ? decimal.toFixed(2) : "—"}</b>
        <small>Analytical payout equivalent</small>
      </div>
      {legs.length>0 && <button className="outline-btn" onClick={onReset} data-testid="reset-build"><RefreshCw size={14}/> RESET</button>}
    </div>
    <div className="legs-list">
      {legs.length === 0 ? <p className="legs-empty">Pick events to see joint probability</p> : legs.map((l,i)=><div className="leg-row" data-testid={`leg-${i}`} key={`${l.fixtureId||"sgm"}-${l.market}-${i}`}><span className="leg-num">0{i+1}</span><div className="leg-body"><b>{l.selection}</b><small>{l.market}{l.fixtureLabel?` · ${l.fixtureLabel}`:""}</small></div><strong>{l.probability}%</strong></div>)}
    </div>
  </div>;
}
function FixturePickChip({fixture, active, disabled, onClick, testid}) {
  return <button className={`f-chip ${active?"active":""}`} disabled={disabled} onClick={onClick} data-testid={testid}>
    <small>{fixture.format} · {fixture.competition}</small>
    <b>{fixture.teams[0]} <i>vs</i> {fixture.teams[1]}</b>
    <span>{fmt(fixture.start_time)}</span>
  </button>;
}
function SgmBuilder({fixtures}) {
  const [fid, setFid] = useState(() => localStorage.getItem("ce.sgm.fid") || "");
  const [legs, setLegs] = useState(() => { try { return JSON.parse(localStorage.getItem("ce.sgm.legs")) || []; } catch { return []; }});
  const events = useFixtureEvents(fid);
  useEffect(() => { localStorage.setItem("ce.sgm.fid", fid); }, [fid]);
  useEffect(() => { localStorage.setItem("ce.sgm.legs", JSON.stringify(legs)); }, [legs]);
  // Clear stale fid if it isn't in the current slate
  useEffect(() => { if (fid && fixtures.length && !fixtures.find(f=>f.id===fid)) { setFid(""); setLegs([]); } }, [fid, fixtures]);
  const pickFixture = (id) => { if (id !== fid) { setFid(id); setLegs([]); } };
  const toggle = (event) => {
    setLegs(prev => prev.some(l=>l.market===event.market)
      ? prev.filter(l=>l.market!==event.market)
      : [...prev, {market:event.market, selection:event.selection, probability:event.probability}]);
  };
  const fixture = fixtures.find(f=>f.id===fid);
  return <div className="builder">
    <div className="builder-block">
      <div className="builder-heading"><span className="eyebrow">1 · PICK ONE FIXTURE</span><small>All legs must come from this match</small></div>
      <div className="fixture-chip-grid" data-testid="sgm-fixture-picker">
        {fixtures.length===0 ? <div className="loading">No fixtures available</div> : fixtures.map(f=><FixturePickChip key={f.id} fixture={f} active={fid===f.id} onClick={()=>pickFixture(f.id)} testid={`sgm-fixture-${f.id}`}/>)}
      </div>
    </div>
    {fid && fixture && <div className="builder-block">
      <div className="builder-heading"><span className="eyebrow">2 · TOGGLE EVENTS · {legs.length} SELECTED</span><small>{fixture.teams[0]} vs {fixture.teams[1]} · {events.length} markets</small></div>
      <div className="event-list" data-testid="sgm-event-list">
        {events.length===0 ? <div className="loading">Loading events…</div> : events.map(e=>{
          const active = legs.some(l=>l.market===e.market);
          return <button key={e.market} className={`event-row ${active?"active":""}`} onClick={()=>toggle(e)} data-testid={`sgm-event-${e.market.replace(/[^a-z0-9]/gi,'-').toLowerCase()}`}>
            <div className="event-check">{active ? "✓" : "+"}</div>
            <div className="event-body"><b>{e.selection}</b><small>{e.market} · {e.confidence} confidence</small></div>
            <strong>{e.probability}%</strong>
          </button>;
        })}
      </div>
    </div>}
    <BuildSummary legs={legs} label="SAME-GAME MULTI" onReset={()=>setLegs([])}/>
  </div>;
}
function MultibetLegPicker({fixture, pick, onPick, idx}) {
  const events = useFixtureEvents(fixture.id);
  return <div className="leg-picker" data-testid={`multi-leg-picker-${idx}`}>
    <div className="leg-picker-head"><span className="eyebrow">LEG 0{idx+1} · {fixture.format}</span><b>{fixture.teams[0]} <i>vs</i> {fixture.teams[1]}</b></div>
    <div className="event-mini-grid">
      {events.length===0 ? <div className="loading">Loading…</div> : events.map(e=>{
        const active = pick?.market===e.market;
        return <button key={e.market} className={`event-mini ${active?"active":""}`} onClick={()=>onPick(fixture.id, e)} data-testid={`multi-event-${idx}-${e.market.replace(/[^a-z0-9]/gi,'-').toLowerCase()}`}>
          <small>{e.market}</small>
          <b>{e.selection}</b>
          <span>{e.probability}%</span>
        </button>;
      })}
    </div>
  </div>;
}
function MultibetBuilder({fixtures}) {
  const [picks, setPicks] = useState(() => { try { return JSON.parse(localStorage.getItem("ce.multi.picks")) || []; } catch { return []; }});
  useEffect(() => { localStorage.setItem("ce.multi.picks", JSON.stringify(picks)); }, [picks]);
  // Drop picks whose fixture is no longer in the slate
  useEffect(() => { if (fixtures.length) { setPicks(prev => prev.filter(p => fixtures.find(f=>f.id===p.fixtureId))); } }, [fixtures]);
  const selectedIds = picks.map(p=>p.fixtureId);
  const canAdd = selectedIds.length < 10;
  const toggleFixture = (fid) => {
    if (selectedIds.includes(fid)) setPicks(prev => prev.filter(p=>p.fixtureId!==fid));
    else if (canAdd) setPicks(prev => [...prev, {fixtureId: fid, market: null, selection: null, probability: null}]);
  };
  const setPick = (fid, event) => setPicks(prev => prev.map(p => p.fixtureId===fid ? {...p, market:event.market, selection:event.selection, probability:event.probability} : p));
  const legs = picks
    .filter(p=>p.probability!=null)
    .map(p => { const f = fixtures.find(fx=>fx.id===p.fixtureId); return {...p, fixtureLabel: f ? `${f.teams[0]} vs ${f.teams[1]}` : ""}; });
  return <div className="builder">
    <div className="builder-block">
      <div className="builder-heading"><span className="eyebrow">1 · PICK UP TO 10 FIXTURES · {picks.length}/10</span><small>Cross-format allowed. Pick one event per fixture below.</small></div>
      <div className="fixture-chip-grid" data-testid="multi-fixture-picker">
        {fixtures.length===0 ? <div className="loading">No fixtures available</div> : fixtures.map(f=>{
          const isSelected = selectedIds.includes(f.id);
          return <FixturePickChip key={f.id} fixture={f} active={isSelected} disabled={!isSelected && !canAdd} onClick={()=>toggleFixture(f.id)} testid={`multi-fixture-${f.id}`}/>;
        })}
      </div>
    </div>
    {picks.length>0 && <div className="builder-block">
      <div className="builder-heading"><span className="eyebrow">2 · PICK ONE EVENT PER LEG</span><small>{legs.length}/{picks.length} legs set</small></div>
      <div className="legs-picker-stack">{picks.map((pick,idx)=>{const fixture = fixtures.find(f=>f.id===pick.fixtureId); return fixture ? <MultibetLegPicker key={pick.fixtureId} fixture={fixture} pick={pick} onPick={setPick} idx={idx}/> : null;})}</div>
    </div>}
    <BuildSummary legs={legs} label="MULTIBET" onReset={()=>setPicks([])}/>
  </div>;
}
function Portfolio() {
  const [mode, setMode] = useState(() => localStorage.getItem("ce.portfolio.mode") || "SGM");
  const [fixtures, setFixtures] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { axios.get(`${API}/fixtures`).then(r=>setFixtures(r.data)).catch(()=>{}).finally(()=>setLoading(false)); }, []);
  const switchMode = (m) => { setMode(m); localStorage.setItem("ce.portfolio.mode", m); };
  return <Shell><div className="page">
    <div className="page-intro">
      <div><div className="eyebrow accent">COMBINATION ENGINE / INTERACTIVE BUILDER</div><h1>Portfolios</h1><p>Build a same-game multi or a cross-fixture multibet. Joint probability updates live.</p></div>
    </div>
    <div className="disclaimer" data-testid="portfolio-disclaimer"><ShieldCheck size={17}/><span><b>READ-ONLY ANALYSIS</b> Joint probability uses a transparent independence approximation. Not wagering advice.</span></div>
    <div className="mode-tabs" data-testid="portfolio-mode-tabs" role="tablist">
      <button className={mode==="SGM"?"active":""} onClick={()=>switchMode("SGM")} data-testid="mode-sgm"><Layers3 size={14}/> Same-game multi<small>Multiple events · one fixture</small></button>
      <button className={mode==="MULTI"?"active":""} onClick={()=>switchMode("MULTI")} data-testid="mode-multi"><Target size={14}/> Multibet<small>One event · up to 10 fixtures</small></button>
    </div>
    {loading ? <div className="loading" data-testid="portfolio-loading">Loading fixtures…</div> : mode==="SGM" ? <SgmBuilder fixtures={fixtures}/> : <MultibetBuilder fixtures={fixtures}/>}
  </div></Shell>;
}
function History() { const [data,setData]=useState(null); useEffect(()=>{axios.get(`${API}/analytics/history`).then(r=>setData(r.data))},[]); return <Shell><div className="page"><div className="page-intro"><div><div className="eyebrow accent">MODEL EVALUATION / HISTORIC</div><h1>Performance</h1><p>Calibration and accuracy from the chronological Cricsheet backtest.</p></div><span className="tag green">● TRACKING HEALTHY</span></div>{data&&<><div className="history-source" data-testid="history-source"><Database size={15}/><span><b>{data.dataset}</b> · Derived from Cricsheet JSON · <a href={data.source} target="_blank" rel="noreferrer" data-testid="history-source-link">SOURCE ARCHIVE ↗</a></span></div><div className="metrics"><Metric label="Accuracy" value={`${data.metrics.accuracy}%`} delta="Chronological baseline" icon={Target}/><Metric label="Brier score" value={data.metrics.brier} delta="Lower is better" icon={Gauge}/><Metric label="Tracked outcomes" value={data.metrics.tracked.toLocaleString()} delta="Real match results" icon={Database}/><Metric label="Calibration" value={`${data.metrics.calibration}%`} delta="Backtest estimate" icon={TrendingUp}/></div><div className="chart-panel"><div className="panel-title"><div><span className="eyebrow">SEASON-BY-SEASON VIEW</span><h2>Accuracy trend</h2></div><span className="mono">ACCURACY %</span></div><div className="chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data.series}><XAxis dataKey="month" stroke="#666"/><YAxis domain={[0,100]} stroke="#666"/><Tooltip contentStyle={{background:"#1b1b1b",border:"1px solid #333"}}/><Area type="monotone" dataKey="accuracy" stroke="#ff3b30" fill="#ff3b30" fillOpacity={.12} strokeWidth={3}/><Area type="monotone" dataKey="calibration" stroke="#34c759" fill="none" strokeWidth={2}/></AreaChart></ResponsiveContainer></div></div><div className="table-panel"><div className="panel-title"><div><span className="eyebrow">MARKET BREAKDOWN</span><h2>Tracked performance</h2></div></div><table><thead><tr><th>MARKET</th><th>SAMPLES</th><th>ACCURACY</th><th>BRIER SCORE</th></tr></thead><tbody>{data.markets.map(m=><tr data-testid={`market-row-${m.name.toLowerCase().replace(' ','-')}`} key={m.name}><td>{m.name}</td><td>{m.samples}</td><td className="green-text">{m.accuracy}</td><td>{m.brier}</td></tr>)}</tbody></table></div></>}</div></Shell> }
function Model() { const [data,setData]=useState(null); useEffect(()=>{axios.get(`${API}/analytics/model`).then(r=>setData(r.data))},[]); return <Shell><div className="page"><div className="page-intro"><div><div className="eyebrow accent">MODEL REGISTRY / EXPLAINABILITY</div><h1>Model insight</h1><p>What moves the probability signal, and how the ensemble is versioned.</p></div><span className="tag green">● ACTIVE</span></div>{data&&<><div className="model-banner"><div><span className="eyebrow">CURRENT PRODUCTION CANDIDATE</span><h2>{data.version}</h2></div><div><span className="eyebrow">LAST TRAINED</span><b>{data.trained}</b></div><div><span className="eyebrow">PIPELINE</span><b className="green-text">● COMPLETE</b></div></div><div className="panel feature-panel"><div className="panel-title"><div><span className="eyebrow">FEATURE IMPORTANCE</span><h2>Signal drivers</h2></div><span className="mono">XGBOOST / ENSEMBLE</span></div><div className="feature-chart"><ResponsiveContainer width="100%" height="100%"><BarChart layout="vertical" data={data.features} margin={{left:20,right:30}}><XAxis type="number" stroke="#666"/><YAxis type="category" dataKey="name" width={150} stroke="#aaa"/><Tooltip contentStyle={{background:"#1b1b1b",border:"1px solid #333"}}/><Bar dataKey="importance" fill="#ff3b30" radius={[0,2,2,0]}/></BarChart></ResponsiveContainer></div></div></>}</div></Shell> }
function App(){return <BrowserRouter><Routes><Route path="/" element={<Overview/>}/><Route path="/fixture/:id" element={<Detail/>}/><Route path="/portfolio" element={<Portfolio/>}/><Route path="/history" element={<History/>}/><Route path="/model" element={<Model/>}/></Routes></BrowserRouter>}
export default App;