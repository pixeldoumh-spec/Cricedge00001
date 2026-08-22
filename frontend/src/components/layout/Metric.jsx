export default function Metric({ label, value, delta, icon: Icon }) {
  return (
    <div className="metric" data-testid={`metric-${label.toLowerCase().replaceAll(" ", "-")}`}>
      <div className="metric-top"><span>{label}</span><Icon size={16}/></div>
      <b>{value}</b>
      <small className={delta?.startsWith("+") ? "up" : ""}>{delta}</small>
    </div>
  );
}
