import { Activity, ChevronRight, CircleHelp, Layers3, ShieldCheck } from "lucide-react";
import { NavLink } from "react-router-dom";

const nav = [
  { to: "/", label: "Fixtures", icon: Activity },
  { to: "/portfolio", label: "Portfolios", icon: Layers3 },
];

export default function Shell({ children }) {
  return (
    <div className="app-shell">
      <aside>
        <div className="brand"><span className="brand-mark">CE</span><span>Cric<span>Edge</span><small>ANALYTICS ENGINE</small></span></div>
        <div className="nav-label">WORKSPACE</div>
        <nav>{nav.map(({ to, label, icon: Icon }) => <NavLink data-testid={`nav-${label.toLowerCase().replace(" ", "-")}`} key={to} to={to} end={to === "/"}><Icon size={17}/>{label}<ChevronRight className="nav-arrow" size={14}/></NavLink>)}</nav>
        <div className="side-status"><div className="live-dot"/> DATA PIPELINE <strong>OPERATIONAL</strong><p>Last normalized<br/><b>2 min ago</b></p></div>
        <div className="side-footer"><ShieldCheck size={15}/> Read-only environment<br/><span>v0.8.2 · UTC</span></div>
      </aside>
      <main>
        <header className="topbar"><div className="crumb"><span>CRICEDGE</span><ChevronRight size={14}/><b>ANALYTICS</b></div><div className="top-actions"><span className="sync"><span className="live-dot"/> LIVE FEED</span><button data-testid="help-button" className="icon-btn" title="Help"><CircleHelp size={18}/></button><div className="avatar">CE</div></div></header>
        {children}
      </main>
    </div>
  );
}
