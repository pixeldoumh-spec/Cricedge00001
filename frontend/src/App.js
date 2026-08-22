import { BrowserRouter, Routes, Route } from "react-router-dom";
import Overview from "@/pages/Overview";
import FixtureDetail from "@/pages/FixtureDetail";
import Portfolio from "@/pages/Portfolio";
import "@/App.css";

export default function App() {
  return <BrowserRouter><Routes><Route path="/" element={<Overview/>}/><Route path="/fixture/:id" element={<FixtureDetail/>}/><Route path="/portfolio" element={<Portfolio/>}/></Routes></BrowserRouter>;
}
