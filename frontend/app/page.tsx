"use client";

import { useState, useEffect, useCallback } from "react";
import { api, authFetch, ScanResponse, ArbOpportunity } from "@/lib/api";
import {
  formatCurrency,
  formatPercent,
  formatOddsAmerican,
  formatSportName,
  formatGameTime,
  timeAgo,
  timeUntilGame,
  gameUrgency,
  urgencyColor,
  urgencyBgColor,
} from "@/lib/utils";

// ─── Stat Card ───────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  color = "text-text-primary",
}: {
  label: string;
  value: string;
  sub?: string;
  color?: string;
}) {
  return (
    <div className="bg-bg-card border border-bg-border rounded-xl px-5 py-4">
      <p className="text-[11px] font-mono text-text-muted uppercase tracking-wider mb-1">
        {label}
      </p>
      <p className={`text-2xl font-mono font-bold tabular-nums ${color}`}>{value}</p>
      {sub && <p className="text-xs text-text-muted mt-1">{sub}</p>}
    </div>
  );
}

// ─── Arb Card ────────────────────────────────────────────────────────────────

function ArbCard({ arb, bankroll, onTrack }: { arb: ArbOpportunity; bankroll: number; onTrack: (arb: ArbOpportunity) => void }) {
  const [expanded, setExpanded] = useState(false);
  const urgency = gameUrgency(arb.commence_time);

  return (
    <div
      className={`bg-bg-card border rounded-xl overflow-hidden card-hover cursor-pointer ${urgency === "dead" ? "border-bg-border opacity-50" : "border-bg-border"}`}
      onClick={() => setExpanded(!expanded)}
    >
      {/* Header */}
      <div className="px-5 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-mono font-bold px-2 py-1 rounded-md bg-accent-blueDim text-accent-blue uppercase">
            {formatSportName(arb.sport)}
          </span>
          <span className={`text-[10px] font-mono font-bold px-2 py-1 rounded-md ${urgencyBgColor(urgency)}`}>
            {urgency === "dead" ? "STARTED" : urgency === "urgent" ? "ACT NOW" : urgency === "soon" ? "SOON" : timeUntilGame(arb.commence_time)}
          </span>
          <div>
            <p className="font-semibold text-text-primary text-sm">{arb.event_name}</p>
            <p className="text-xs text-text-muted mt-0.5">
              {formatGameTime(arb.commence_time)}
            </p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-xl font-mono font-bold text-accent-green glow-green tabular-nums">
            {formatPercent(arb.profit_percentage)}
          </p>
          <p className="text-xs font-mono text-accent-green tabular-nums">
            {formatCurrency(arb.guaranteed_profit)} guaranteed
          </p>
        </div>
      </div>

      {/* Bet Split Bar */}
      <div className="px-5 pb-3 flex gap-3">
        <div className="flex-1 bg-bg-hover rounded-lg px-4 py-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] font-mono text-text-muted uppercase">{arb.book_a}</span>
            <span className="text-xs font-mono text-text-secondary">
              {formatOddsAmerican(arb.odds_a_american)}
            </span>
          </div>
          <p className="text-sm font-semibold text-text-primary">{arb.outcome_a}</p>
          <p className="text-lg font-mono font-bold text-accent-yellow tabular-nums mt-1">
            {formatCurrency(arb.stake_a)}
          </p>
        </div>
        <div className="flex items-center text-text-muted text-xs font-mono">VS</div>
        <div className="flex-1 bg-bg-hover rounded-lg px-4 py-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] font-mono text-text-muted uppercase">{arb.book_b}</span>
            <span className="text-xs font-mono text-text-secondary">
              {formatOddsAmerican(arb.odds_b_american)}
            </span>
          </div>
          <p className="text-sm font-semibold text-text-primary">{arb.outcome_b}</p>
          <p className="text-lg font-mono font-bold text-accent-yellow tabular-nums mt-1">
            {formatCurrency(arb.stake_b)}
          </p>
        </div>
        {arb.outcome_c && (
          <>
            <div className="flex items-center text-text-muted text-xs font-mono">VS</div>
            <div className="flex-1 bg-bg-hover rounded-lg px-4 py-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-mono text-text-muted uppercase">
                  {arb.book_c}
                </span>
                <span className="text-xs font-mono text-text-secondary">
                  {arb.odds_c_american != null ? formatOddsAmerican(arb.odds_c_american) : ""}
                </span>
              </div>
              <p className="text-sm font-semibold text-text-primary">{arb.outcome_c}</p>
              <p className="text-lg font-mono font-bold text-accent-yellow tabular-nums mt-1">
                {arb.stake_c != null ? formatCurrency(arb.stake_c) : ""}
              </p>
            </div>
          </>
        )}
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="px-5 py-4 border-t border-bg-border bg-bg-secondary animate-fade-in">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-[10px] font-mono text-text-muted uppercase">Total Stake</p>
              <p className="font-mono font-bold text-text-primary tabular-nums">
                {formatCurrency(arb.total_stake)}
              </p>
            </div>
            <div>
              <p className="text-[10px] font-mono text-text-muted uppercase">Guaranteed Return</p>
              <p className="font-mono font-bold text-accent-green tabular-nums">
                {formatCurrency(arb.guaranteed_return)}
              </p>
            </div>
            <div>
              <p className="text-[10px] font-mono text-text-muted uppercase">Arb Margin</p>
              <p className="font-mono font-bold text-text-primary tabular-nums">
                {(arb.arb_margin * 100).toFixed(2)}%
              </p>
            </div>
            <div>
              <p className="text-[10px] font-mono text-text-muted uppercase">ROI</p>
              <p className="font-mono font-bold text-accent-green glow-green tabular-nums">
                {formatPercent(arb.profit_percentage)}
              </p>
            </div>
          </div>
          <div className="mt-4 flex items-center justify-between">
            <div className="flex items-center gap-3 text-xs text-text-muted font-mono">
              {(arb as any).book_a_trusted !== undefined && (
                <span className={(arb as any).book_a_trusted ? "text-accent-green" : "text-accent-red"}>
                  {(arb as any).book_a_display || arb.book_a}: {(arb as any).book_a_trusted ? "Trusted" : "Unverified"}
                </span>
              )}
              {(arb as any).book_b_trusted !== undefined && (
                <span className={(arb as any).book_b_trusted ? "text-accent-green" : "text-accent-red"}>
                  {(arb as any).book_b_display || arb.book_b}: {(arb as any).book_b_trusted ? "Trusted" : "Unverified"}
                </span>
              )}
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); onTrack(arb); }}
              className="px-4 py-2 rounded-lg text-sm font-semibold bg-accent-green text-bg-primary hover:brightness-110 transition-all"
            >
              Track Bet
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Empty State ─────────────────────────────────────────────────────────────

function EmptyState({ scanned }: { scanned: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-16 h-16 rounded-2xl bg-bg-hover border border-bg-border flex items-center justify-center mb-4">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-text-muted">
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
      </div>
      <p className="text-text-secondary font-medium mb-1">
        {scanned ? "No arb opportunities right now" : "Ready to scan"}
      </p>
      <p className="text-sm text-text-muted max-w-sm">
        {scanned
          ? "Arb windows are rare and short-lived. Try scanning again later, especially before game times when lines move fast."
          : 'Hit "Scan Now" to check all sportsbooks for arbitrage opportunities.'}
      </p>
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [data, setData] = useState<ScanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasScanned, setHasScanned] = useState(false);
  const [autoScan, setAutoScan] = useState(false);
  const [autoScanInterval, setAutoScanInterval] = useState(120);

  const runScan = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.scan({ min_profit: 0.1 });
      setData(result);
      setHasScanned(true);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Auto-refresh cached results when auto-scan is on
  useEffect(() => {
    if (!autoScan) return;
    const interval = setInterval(async () => {
      try {
        const result = await api.getLatestArbs();
        setData(result);
      } catch (e) {
        // silent fail on cache refresh
      }
    }, 10000); // refresh UI every 10s
    return () => clearInterval(interval);
  }, [autoScan]);

  const toggleAutoScan = async () => {
    try {
      if (!autoScan) {
        await api.setAutoScan({ enabled: true, interval_seconds: autoScanInterval });
        setAutoScan(true);
        // Do an initial scan immediately
        runScan();
      } else {
        await api.setAutoScan({ enabled: false });
        setAutoScan(false);
      }
    } catch (e: any) {
      setError(e.message);
    }
  };

  const opportunities = data?.opportunities ?? [];
  const totalProfit = opportunities.reduce((sum, a) => sum + a.guaranteed_profit, 0);

  const [trackMessage, setTrackMessage] = useState<string | null>(null);

  const trackBet = async (arb: ArbOpportunity) => {
    try {
      await authFetch("/bets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(arb),
      });
      setTrackMessage(`Tracked: ${arb.event_name}`);
      setTimeout(() => setTrackMessage(null), 3000);
    } catch (e) {
      setTrackMessage("Failed to track bet");
      setTimeout(() => setTrackMessage(null), 3000);
    }
  };

  return (
    <div className="px-8 py-6 max-w-[1400px]">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-text-primary">Live Scanner</h2>
          <p className="text-sm text-text-muted mt-0.5">
            Scan sportsbooks for arbitrage opportunities
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Auto-scan toggle */}
          <button
            onClick={toggleAutoScan}
            className={`
              flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all border
              ${
                autoScan
                  ? "bg-accent-greenDim border-accent-green/30 text-accent-green"
                  : "bg-bg-card border-bg-border text-text-secondary hover:text-text-primary hover:border-bg-hover"
              }
            `}
          >
            <span className={`w-2 h-2 rounded-full ${autoScan ? "bg-accent-green pulse-green" : "bg-text-muted"}`} />
            Auto-Scan {autoScan ? "ON" : "OFF"}
          </button>

          {/* Scan button */}
          <button
            onClick={runScan}
            disabled={loading}
            className={`
              px-5 py-2.5 rounded-lg text-sm font-semibold transition-all
              ${
                loading
                  ? "bg-bg-hover text-text-muted cursor-wait"
                  : "bg-accent-green text-bg-primary hover:brightness-110"
              }
            `}
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Scanning...
              </span>
            ) : (
              "Scan Now"
            )}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-accent-redDim border border-accent-red/30 text-accent-red text-sm">
          {error}
        </div>
      )}

      {/* Track confirmation toast */}
      {trackMessage && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-accent-greenDim border border-accent-green/30 text-accent-green text-sm animate-fade-in">
          {trackMessage} — <a href="/history" className="underline font-semibold">View in History</a>
        </div>
      )}

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Arbs Found"
          value={String(opportunities.length)}
          color={opportunities.length > 0 ? "text-accent-green" : "text-text-primary"}
        />
        <StatCard
          label="Events Scanned"
          value={String(data?.events_scanned ?? 0)}
          sub={data ? `${data.sports_scanned.length} sports` : undefined}
        />
        <StatCard
          label="Total Potential"
          value={totalProfit > 0 ? formatCurrency(totalProfit) : "$0.00"}
          sub={totalProfit > 0 ? `across ${opportunities.length} arbs` : undefined}
          color={totalProfit > 0 ? "text-accent-green" : "text-text-primary"}
        />
        <StatCard
          label="API Requests Left"
          value={
            data?.api_usage?.total_remaining != null && data.api_usage.total_remaining > 0
              ? String(data.api_usage.total_remaining)
              : data?.api_usage?.untested_keys
                ? `${data.api_usage.total_keys} key(s)`
                : "---"
          }
          sub={data?.scan_time ? `Last: ${timeAgo(data.scan_time)}` : "Run a scan to check"}
        />
      </div>

      {/* Arb List */}
      {opportunities.length > 0 ? (
        <div className="space-y-3 stagger-children">
          {opportunities.map((arb, i) => (
            <ArbCard key={`${arb.event_name}-${arb.book_a}-${arb.book_b}-${i}`} arb={arb} bankroll={data?.bankroll ?? 1000} onTrack={trackBet} />
          ))}
        </div>
      ) : (
        <EmptyState scanned={hasScanned} />
      )}
    </div>
  );
}