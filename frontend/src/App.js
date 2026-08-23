import React from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import Overview from "@/pages/Overview";
import FixtureDetail from "@/pages/FixtureDetail";
import Portfolio from "@/pages/Portfolio";
import "@/App.css";

class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, message: "" };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      message: error?.message || "An unexpected application error occurred.",
    };
  }

  componentDidCatch(error, info) {
    // Keep the user-facing message safe while retaining diagnostics in development.
    if (process.env.NODE_ENV !== "production") {
      console.error("CricEdge render error", error, info);
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, message: "" });
  };

  render() {
    if (this.state.hasError) {
      return (
        <main className="page" role="alert" aria-live="assertive">
          <div className="page-intro">
            <div>
              <span className="eyebrow accent">CRICEDGE / RECOVERY</span>
              <h1>Something went wrong.</h1>
              <p>We could not render this view safely. Your saved portfolio data was not changed.</p>
            </div>
          </div>
          <div className="detail-cta">
            <div><span className="eyebrow">NEXT STEP</span><b>{this.state.message}</b></div>
            <div>
              <button type="button" className="outline-btn" onClick={this.handleRetry}>TRY AGAIN</button>
              <Link className="outline-btn" to="/">HOME</Link>
            </div>
          </div>
        </main>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  return (
    <AppErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/fixture/:id" element={<FixtureDetail />} />
          <Route path="/portfolio" element={<Portfolio />} />
        </Routes>
      </BrowserRouter>
    </AppErrorBoundary>
  );
}
