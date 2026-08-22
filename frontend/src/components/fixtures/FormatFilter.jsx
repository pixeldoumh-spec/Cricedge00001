export default function FormatFilter({ formats = [], active, onChange, total = 0 }) {
  const chips = [
    { key: "ALL", label: "All formats", count: total, profile: "Full cricket slate" },
    ...formats.map((format) => ({ key: format.key, label: format.label, count: format.count, profile: format.profile })),
  ];

  return (
    <div className="format-filter" data-testid="format-filter">
      <div className="filter-label">
        <span className="eyebrow">FORMAT STRATEGY</span>
        <small>Predictions adapt to each format</small>
      </div>
      <div className="chip-row">
        {chips.map((chip) => {
          const disabled = chip.count === 0 && chip.key !== "ALL";
          return (
            <button
              key={chip.key}
              data-testid={`format-chip-${chip.key.toLowerCase()}`}
              className={`chip ${active === chip.key ? "active" : ""} ${disabled ? "empty" : ""}`}
              onClick={() => onChange(chip.key)}
              disabled={disabled}
              title={chip.profile}
            >
              <span>{chip.label}</span>
              <b>{chip.count}</b>
            </button>
          );
        })}
      </div>
    </div>
  );
}
