export default function MarketsBoard({ markets = [], activeKeys, onSelect, filter }) {
  const groups = markets.reduce((acc, market) => {
    (acc[market.group] ||= []).push(market);
    return acc;
  }, {});

  const groupOrder = ["Match", "Innings totals", "Match specials", "Phase", "Player", "Team specials"];
  const orderedGroups = [
    ...groupOrder.filter((group) => groups[group]),
    ...Object.keys(groups).filter((group) => !groupOrder.includes(group)),
  ];
  const shown = filter ? orderedGroups.filter((group) => group === filter) : orderedGroups;

  return (
    <div className="markets-board" data-testid="markets-board">
      {shown.map((group) => (
        <div className="market-group" data-testid={`market-group-${group.toLowerCase().replace(/ /g, "-")}`} key={group}>
          <div className="market-group-head">
            <span className="eyebrow">{group}</span>
            <small>{groups[group].length} markets</small>
          </div>
          {groups[group].map((market) => (
            <div className="market-row" key={market.key} data-testid={`market-${market.key}`}>
              <div className="market-label">
                <b>{market.label}{market.source === "LIVE" && <span className="live-badge" data-testid={`live-badge-${market.key}`}>LIVE</span>}</b>
                <small>{market.line}</small>
              </div>
              <div className="selection-pills">
                {market.selections.map((selection) => {
                  const active = activeKeys?.has(selection.key);
                  return (
                    <button
                      key={selection.key}
                      className={`sel-pill ${active ? "active" : ""}`}
                      onClick={() => onSelect?.(market, selection)}
                      disabled={!onSelect}
                      data-testid={`sel-${selection.key}`}
                    >
                      <span className="sel-name">{selection.name}</span>
                      <div className="sel-values"><b>{selection.price.toFixed(2)}</b><small>{selection.probability}%</small></div>
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
}
