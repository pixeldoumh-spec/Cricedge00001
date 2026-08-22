import { useState } from "react";
import { Layers3, ShieldCheck, Target } from "lucide-react";
import { useFixtures } from "@/hooks/useFixtures";
import Shell from "@/components/layout/Shell";
import SgmBuilder from "@/features/portfolio/SgmBuilder";
import MultibetBuilder from "@/features/portfolio/MultibetBuilder";

const getApiErrorMessage = (error, fallback = "Something went wrong. Please try again.") => error?.userMessage || error?.response?.data?.detail || fallback;

export default function Portfolio() {
  const [mode, setMode] = useState(() => localStorage.getItem("ce.portfolio.mode") || "SGM");
  const { data: fixtures = [], isLoading: loading, error } = useFixtures("ALL");
  const switchMode = (nextMode) => { setMode(nextMode); localStorage.setItem("ce.portfolio.mode", nextMode); };

  return <Shell><div className="page"><div className="page-intro"><div><div className="eyebrow accent">COMBINATION ENGINE / INTERACTIVE BUILDER</div><h1>Portfolios</h1><p>Build a same-game multi or a cross-fixture multibet. Joint probability updates live.</p></div></div>
    <div className="disclaimer" data-testid="portfolio-disclaimer"><ShieldCheck size={17}/><span><b>READ-ONLY ANALYSIS</b> Joint probability uses a transparent independence approximation. Not wagering advice.</span></div>
    <div className="mode-tabs" data-testid="portfolio-mode-tabs" role="tablist"><button className={mode === "SGM" ? "active" : ""} onClick={() => switchMode("SGM")} data-testid="mode-sgm"><Layers3 size={14}/> Same-game multi<small>Multiple events · one fixture</small></button><button className={mode === "MULTI" ? "active" : ""} onClick={() => switchMode("MULTI")} data-testid="mode-multi"><Target size={14}/> Multibet<small>One event · up to 10 fixtures</small></button></div>
    {error ? <div className="loading error" data-testid="portfolio-error">{getApiErrorMessage(error, "Unable to load portfolio fixtures.")}</div> : loading ? <div className="loading" data-testid="portfolio-loading">Loading fixtures…</div> : mode === "SGM" ? <SgmBuilder fixtures={fixtures}/> : <MultibetBuilder fixtures={fixtures}/>}</div></Shell>;
}
