/**
 * API Client for the Arb Finder backend.
 * All requests go through Next.js rewrite -> localhost:8000
 */

const BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Request failed: ${res.status}`);
  }

  return res.json();
}

// ─── Types ──────────────────────────────────────────────────────────────────

export interface StakeInfo {
  book: string;
  stake: number;
  odds_decimal: number;
  odds_american: number;
  potential_return: number;
}

export interface Scenario {
  outcome: string;
  return: number;
  profit: number;
}

export interface CalcResponse {
  is_arb: boolean;
  stakes: Record<string, StakeInfo>;
  total_stake: number;
  guaranteed_return: number;
  guaranteed_profit: number;
  profit_percentage: number;
  profit_after_fees: number | null;
  scenarios: Scenario[];
  combined_implied_probability: number;
  arb_margin: number;
}

export interface ArbOpportunity {
  event_name: string;
  sport: string;
  commence_time: string | null;
  outcome_a: string;
  book_a: string;
  odds_a_decimal: number;
  odds_a_american: number;
  stake_a: number;
  outcome_b: string;
  book_b: string;
  odds_b_decimal: number;
  odds_b_american: number;
  stake_b: number;
  outcome_c?: string | null;
  book_c?: string | null;
  odds_c_decimal?: number | null;
  odds_c_american?: number | null;
  stake_c?: number | null;
  total_stake: number;
  guaranteed_return: number;
  guaranteed_profit: number;
  profit_percentage: number;
  arb_margin: number;
}

export interface ScanResponse {
  opportunities: ArbOpportunity[];
  total_found: number;
  events_scanned: number;
  sports_scanned: string[];
  bankroll: number;
  scan_time: string;
  api_usage: {
    total_remaining?: number;
    total_keys?: number;
    untested_keys?: number;
    current_index?: number;
    keys?: any[];
    remaining_requests?: number;
    used_requests?: number;
  };
}

export interface Settings {
  bankroll: number;
  scan_sports: string[];
  enabled_books: string[];
  min_profit_pct: number;
  max_profit_pct: number;
  auto_scan_interval: number;
  api_keys?: {
    total_keys: number;
    total_remaining: number;
    current_index: number;
    keys: any[];
  };
  notifications?: {
    configured: boolean;
    min_profit_to_notify: number;
  };
  // Legacy fields for backwards compat
  api_key_configured?: boolean;
  api_usage?: any;
}

export interface AutoScanStatus {
  enabled: boolean;
  interval_seconds: number;
  sports: string[];
  bankroll: number;
  last_scan_time: string | null;
  cached_arbs: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  api_key_configured: boolean;
  timestamp: string;
}

// ─── API Functions ──────────────────────────────────────────────────────────

export const api = {
  health: () => request<HealthResponse>("/health".replace("/api", "")),

  scan: (params?: { sports?: string; bankroll?: number; min_profit?: number }) => {
    const query = new URLSearchParams();
    if (params?.sports) query.set("sports", params.sports);
    if (params?.bankroll) query.set("bankroll", String(params.bankroll));
    if (params?.min_profit) query.set("min_profit", String(params.min_profit));
    const qs = query.toString();
    return request<ScanResponse>(`/scan${qs ? `?${qs}` : ""}`);
  },

  getLatestArbs: () => request<ScanResponse>("/arbs"),

  calculate: (body: {
    odds_a: number;
    odds_b: number;
    odds_c?: number;
    odds_format?: string;
    bankroll?: number;
    outcome_a_name?: string;
    outcome_b_name?: string;
    outcome_c_name?: string;
    book_a?: string;
    book_b?: string;
    book_c?: string;
    fee_pct?: number;
  }) => request<CalcResponse>("/calculate", { method: "POST", body: JSON.stringify(body) }),

  getSettings: () => request<Settings>("/settings"),

  updateSettings: (settings: Partial<Settings>) =>
    request("/settings", { method: "PUT", body: JSON.stringify(settings) }),

  getAutoScanStatus: () => request<AutoScanStatus>("/auto-scan"),

  setAutoScan: (config: {
    enabled: boolean;
    interval_seconds?: number;
    bankroll?: number;
    sports?: string[];
  }) => request("/auto-scan", { method: "POST", body: JSON.stringify(config) }),

  getSports: () => request<{ sports: any[]; total: number; configured: string[] }>("/sports"),

  convertOdds: (odds: number, fromFormat: string) =>
    request<{
      decimal: number;
      american: number;
      implied_probability: number;
      implied_probability_pct: number;
    }>(`/convert-odds?odds=${odds}&from_format=${fromFormat}`),

  optimizeBudget: (body: {
    budget: number;
    max_per_arb_pct?: number;
    min_per_arb?: number;
    max_arbs?: number;
  }) => request<any>("/budget", { method: "POST", body: JSON.stringify(body) }),

  getBookRotation: () => request<any>("/book-rotation"),

  getSportsbooks: () => request<any>("/sportsbooks"),
};