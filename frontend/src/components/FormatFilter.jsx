import React from 'react';

export const FormatFilter = ({ formats, active, onChange, total }) => {
  const chips = [
    { key: 'ALL', label: 'All formats', count: total, profile: 'Full cricket slate' },
    ...formats.map((f) => ({
      key: f.key,
      label: f.label,
      count: f.count,
      profile: f.profile,
    })),
  ];

  return (
    <div className="format-filter" data-testid="format-filter">
      <div className="filter-label">
        <span className="eyebrow">FORMAT STRATEGY</span>
        <small>Predictions adapt to each format</small>
      </div>
      <div className="chip-row">
        {chips.map((c) => (
          <button
            key={c.key}
            data-testid={`format-chip-${c.key.toLowerCase()}`}
            className={`chip ${active === c.key ? 'active' : ''} ${
              c.count === 0 && c.key !== 'ALL' ? 'empty' : ''
            }`}
            onClick={() => onChange(c.key)}
            disabled={c.count === 0 && c.key !== 'ALL'}
          >
            <span className="chip-label">{c.label}</span>
            <span className="chip-count">{c.count}</span>
            <span className="chip-profile">{c.profile}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
