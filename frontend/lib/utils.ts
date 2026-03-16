/**
 * Format helpers used throughout the dashboard.
 */

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function formatPercent(pct: number): string {
  return `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%`;
}

export function formatOddsAmerican(odds: number): string {
  return odds >= 0 ? `+${Math.round(odds)}` : `${Math.round(odds)}`;
}

export function formatSportName(key: string): string {
  const map: Record<string, string> = {
    basketball_nba: "NBA",
    americanfootball_nfl: "NFL",
    baseball_mlb: "MLB",
    icehockey_nhl: "NHL",
    soccer_epl: "EPL",
    soccer_usa_mls: "MLS",
    basketball_ncaab: "NCAAB",
    americanfootball_ncaaf: "NCAAF",
    mma_mixed_martial_arts: "MMA",
    soccer_spain_la_liga: "La Liga",
    soccer_italy_serie_a: "Serie A",
    soccer_germany_bundesliga: "Bundesliga",
  };
  return map[key] || key.split("_").pop()?.toUpperCase() || key;
}

export function sportEmoji(key: string): string {
  if (key.includes("basketball")) return ""; // no emojis per user preference
  return "";
}

export function timeAgo(isoString: string | null): string {
  if (!isoString || isoString === "never") return "Never";
  const diff = Date.now() - new Date(isoString).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

export function formatGameTime(isoString: string | null): string {
  if (!isoString) return "TBD";
  const d = new Date(isoString);
  return d.toLocaleString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function timeUntilGame(isoString: string | null): string {
  if (!isoString) return "TBD";
  const diff = new Date(isoString).getTime() - Date.now();
  if (diff <= 0) return "LIVE / Started";
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ${minutes % 60}m`;
  const days = Math.floor(hours / 24);
  return `${days}d ${hours % 24}h`;
}

export function gameUrgency(isoString: string | null): "dead" | "urgent" | "soon" | "safe" {
  if (!isoString) return "safe";
  const diff = new Date(isoString).getTime() - Date.now();
  if (diff <= 0) return "dead";          // Already started
  if (diff < 60 * 60 * 1000) return "urgent";   // < 1 hour
  if (diff < 6 * 60 * 60 * 1000) return "soon"; // < 6 hours
  return "safe";                                  // > 6 hours
}

export function urgencyColor(urgency: "dead" | "urgent" | "soon" | "safe"): string {
  switch (urgency) {
    case "dead": return "text-text-muted";
    case "urgent": return "text-accent-red";
    case "soon": return "text-accent-yellow";
    case "safe": return "text-accent-green";
  }
}

export function urgencyBgColor(urgency: "dead" | "urgent" | "soon" | "safe"): string {
  switch (urgency) {
    case "dead": return "bg-bg-hover border-bg-border text-text-muted";
    case "urgent": return "bg-accent-redDim border-accent-red/30 text-accent-red";
    case "soon": return "bg-accent-yellowDim border-accent-yellow/30 text-accent-yellow";
    case "safe": return "bg-accent-greenDim border-accent-green/30 text-accent-green";
  }
}

export function riskLabel(risk: string): { text: string; color: string } {
  switch (risk) {
    case "low": return { text: "Low Risk", color: "text-accent-green" };
    case "medium": return { text: "Med Risk", color: "text-accent-yellow" };
    case "high": return { text: "High Risk", color: "text-accent-red" };
    default: return { text: "Unknown", color: "text-text-muted" };
  }
}