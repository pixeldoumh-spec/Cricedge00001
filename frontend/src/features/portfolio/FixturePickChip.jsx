import { fmt } from "@/utils/format";

export default function FixturePickChip({ fixture, active, disabled, onClick, testid }) {
  return <button className={`f-chip ${active ? "active" : ""}`} disabled={disabled} onClick={onClick} data-testid={testid}><small>{fixture.format} · {fixture.competition}</small><b>{fixture.teams[0]} <i>vs</i> {fixture.teams[1]}</b><span>{fmt(fixture.start_time)}</span></button>;
}
