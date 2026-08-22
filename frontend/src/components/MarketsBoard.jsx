import React from 'react';
import { ShieldCheck } from 'lucide-react';

export const MarketsBoard = ({ markets, activeKeys, onSelect, filter }) => {
  const groups = markets.reduce((acc, m) => {
    (acc[m.group] ||= []).push(m);
    return acc;
  }, {});

  const groupOrder = [
    'Match',
    'Innings totals',
    'Match specials',
    'Phase',
    'Player',
    'Team specials',
  ];
  const orderedGroups = [
    ...groupOrder.filter((g) => groups[g]),
    ...Object.keys(groups).filter((g) => !groupOrder.includes(g)),
  ];
  const shown = filter ? orderedGroups.filter((g) => g === filter) : orderedGroups;

  return (
    <div className="markets-board" data-testid="markets-board">
      {shown.map((group) => (
        <div
          className="market-group"
          data-testid={`market-group-${group.toLowerCase().replace(/ /g, '-')}`}
          key={group}
        >
          <div className="market-group-head">
            <span className="eyebrow">{group}</span>
            <small>{groups[group].length} markets</small>
          </div>
          {groups[group].map((market) => (
            <div className="market-row" key={market.key} data-testid={`market-${market.key}`}>
              <div className="market-label">
                <b>
                  {market.label}
                  {market.source === 'LIVE' && (
                    <span className="live-badge" data-testid={`live-badge-${market.key}`}>
                      LIVE
                    </span>
                  )}
                </b>
                <small>{market.line}</small>
              </div>
              <div className="selection-pills">
                {market.selections.map((sel) => {
                  const active = activeKeys?.has(sel.key);
                  return (
                    <button
                      key={sel.key}
                      className={`sel-pill ${active ? 'active' : ''}`}
                      onClick={() => onSelect?.(market, sel)}
                      disabled={!onSelect}
                      data-testid={`sel-${sel.key}`}
                    >
                      <span className="sel-name">{sel.name}</span>
                      <div className="sel-values">
                        <b>{sel.price.toFixed(2)}</b>
                        <small>{sel.probability}%</small>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
};
