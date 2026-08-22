export const fmt = (value) => new Date(value).toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" });
