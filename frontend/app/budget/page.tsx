"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import {
  formatCurrency, formatPercent, formatSportName, formatOddsAmerican,
  formatGameTime, timeUntilGame, gameUrgency, urgencyColor, urgencyBgColor, riskLabel,
} from "@/lib/utils";

interface Allocation {
  event_name: string;
  sport: string;
  commence_time?: string | null;
  outcome_a: string;
  book_a: string;
  book_a_display?: string;
  book_a_min_bet?: number;
  book_a_arb_risk?: string;
  stake_a: number;
  odds_a_american: number;
  outcome_b: string;
  book_b: string;
  book_b_display?: string;
  book_b_min_bet?: number;
  book_b_arb_risk?: string;
  stake_b: number;
  odds_b_american: number;
  outcome_c?: string | null;
  book_c?: string | null;
  stake_c?: number | null;
  allocated_amount: number;
  guaranteed_profit: number;
  profit_pct: number;
  rotation_score: number;
}

interface BudgetPlan {
  total_budget: number;
  total_allocated: number;
  total_remaining: number;
  total_guaranteed_profit: number;
  overall_roi: number;
  allocations: Allocation[];
  books_used: Record<string, number>;
  warnings: string[];
}

function StatCard({ label, value, color = "text-text-primary" }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-bg-card border border-bg-border rounded-xl px-5 py-4">
      <p className="text-[11px] font-mono text-text-muted uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-2xl font-mono font-bold tabular-nums ${color}`}>{value}</p>
    </div>
  );
}

export default function BudgetPage() {
  const [budget, setBudget] = useState("500");
  const [plan, setPlan] = useState<BudgetPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const optimize = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.optimizeBudget({
        budget: parseFloat(budget) || 500,
      });
      setPlan(result);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const trackAll = async () => {
    if (!plan) return;
    for (const a of plan.allocations) {
      try {
        await fetch("/api/bets", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            event_name: a.event_name, sport: a.sport,
            outcome_a: a.outcome_a, book_a: a.book_a,
            odds_a_decimal: 0, odds_a_american: a.odds_a_american, stake_a: a.stake_a,
            outcome_b: a.outcome_b, book_b: a.book_b,
            odds_b_decimal: 0, odds_b_american: a.odds_b_american, stake_b: a.stake_b,
            total_stake: a.allocated_amount, guaranteed_return: a.allocated_amount + a.guaranteed_profit,
            guaranteed_profit: a.guaranteed_profit, profit_percentage: a.profit_pct, arb_margin: 0,
          }),
        });
      } catch (e) { /* continue */ }
    }
    alert(`Tracked ${plan.allocations.length} bets. Check History page.`);
  };

  return (
    <div className="px-8 py-6 max-w-[1400px]">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-text-primary">Budget Optimizer</h2>
        <p className="text-sm text-text-muted mt-0.5">
          Set your total budget and get the optimal split across multiple arbs, with book rotation built in
        </p>
      </div>

      {/* Input */}
      <div className="bg-bg-card border border-bg-border rounded-xl p-6 mb-6">
        <div className="mb-4">
          <label className="block text-[11px] font-mono text-text-muted uppercase tracking-wider mb-1.5">How much do you want to put down total? ($)</label>
          <input type="number" value={budget} onChange={(e) => setBudget(e.target.value)}
            placeholder="e.g. 500"
            className="w-full bg-bg-hover border border-bg-border rounded-lg px-4 py-3 font-mono text-lg text-text-primary focus:outline-none focus:border-accent-green/50 transition-all" />
        </div>
        <p className="text-xs text-text-muted mb-4">
          The system will analyze all current arb opportunities, determine the best combination, spread your bets across different sportsbooks to avoid detection, and tell you exactly where to place each bet.
        </p>
        {error && (
          <div className="mb-4 px-4 py-3 rounded-lg bg-accent-redDim border border-accent-red/30 text-accent-red text-sm">{error}</div>
        )}
        <button onClick={optimize} disabled={loading}
          className={`w-full py-3 rounded-lg font-semibold text-sm transition-all ${loading ? "bg-bg-hover text-text-muted cursor-wait" : "bg-accent-green text-bg-primary hover:brightness-110"}`}>
          {loading ? "Optimizing..." : "Optimize Budget"}
        </button>
      </div>

      {/* Results */}
      {plan && (
        <>
          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
            <StatCard label="Total Budget" value={formatCurrency(plan.total_budget)} />
            <StatCard label="Allocated" value={formatCurrency(plan.total_allocated)} />
            <StatCard label="Remaining" value={formatCurrency(plan.total_remaining)} color="text-text-secondary" />
            <StatCard label="Guaranteed Profit" value={formatCurrency(plan.total_guaranteed_profit)} color="text-accent-green" />
            <StatCard label="Overall ROI" value={formatPercent(plan.overall_roi)} color="text-accent-green" />
          </div>

          {/* Warnings */}
          {plan.warnings.length > 0 && (
            <div className="mb-4 space-y-2">
              {plan.warnings.map((w, i) => (
                <div key={i} className="px-4 py-3 rounded-lg bg-accent-yellowDim border border-accent-yellow/30 text-accent-yellow text-sm">{w}</div>
              ))}
            </div>
          )}

          {/* Book Usage */}
          {Object.keys(plan.books_used).length > 0 && (
            <div className="bg-bg-card border border-bg-border rounded-xl p-5 mb-6">
              <p className="text-[11px] font-mono text-text-muted uppercase tracking-wider mb-3">Book Usage in This Plan</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(plan.books_used).map(([book, count]) => (
                  <span key={book} className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium border ${
                    count >= 3 ? "bg-accent-redDim border-accent-red/30 text-accent-red" :
                    count >= 2 ? "bg-accent-yellowDim border-accent-yellow/30 text-accent-yellow" :
                    "bg-accent-greenDim border-accent-green/30 text-accent-green"
                  }`}>
                    {book}: {count}x
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Allocations */}
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-semibold text-text-primary">{plan.allocations.length} Arb Allocation{plan.allocations.length !== 1 ? "s" : ""}</p>
            {plan.allocations.length > 0 && (
              <button onClick={trackAll}
                className="px-4 py-2 rounded-lg text-sm font-semibold bg-accent-blue text-bg-primary hover:brightness-110 transition-all">
                Track All Bets
              </button>
            )}
          </div>
          <div className="space-y-3 stagger-children">
            {plan.allocations.map((a, i) => {
              const urgency = gameUrgency(a.commence_time || null);
              const minBetWarningA = a.book_a_min_bet && a.stake_a < a.book_a_min_bet;
              const minBetWarningB = a.book_b_min_bet && a.stake_b < a.book_b_min_bet;
              const riskA = riskLabel(a.book_a_arb_risk || "unknown");
              const riskB = riskLabel(a.book_b_arb_risk || "unknown");

              return (
              <div key={i} className={`bg-bg-card border rounded-xl px-5 py-4 ${urgency === "dead" ? "border-bg-border opacity-50" : "border-bg-border"}`}>
                {/* Header: sport, event, time, profit */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] font-mono font-bold px-2 py-1 rounded-md bg-accent-blueDim text-accent-blue uppercase">
                      {formatSportName(a.sport)}
                    </span>
                    <span className={`text-[10px] font-mono font-bold px-2 py-1 rounded-md ${urgencyBgColor(urgency)}`}>
                      {urgency === "dead" ? "STARTED" : urgency === "urgent" ? "ACT NOW" : urgency === "soon" ? "SOON" : "SAFE"}
                    </span>
                    <div>
                      <span className="text-sm font-semibold text-text-primary">{a.event_name}</span>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-xs text-text-muted">{formatGameTime(a.commence_time || null)}</span>
                        <span className={`text-xs font-mono font-semibold ${urgencyColor(urgency)}`}>
                          {timeUntilGame(a.commence_time || null)}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-mono font-bold text-accent-green glow-green tabular-nums">{formatCurrency(a.guaranteed_profit)}</p>
                    <p className="text-[10px] font-mono text-text-muted">{formatPercent(a.profit_pct)} ROI</p>
                  </div>
                </div>

                {/* Bet cards */}
                <div className="flex gap-3">
                  <div className={`flex-1 bg-bg-hover rounded-lg px-4 py-3 ${minBetWarningA ? "border border-accent-red/30" : ""}`}>
                    <div className="flex justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono text-text-muted uppercase">{a.book_a_display || a.book_a}</span>
                        <span className={`text-[9px] font-mono ${riskA.color}`}>{riskA.text}</span>
                      </div>
                      <span className="text-xs font-mono text-text-secondary">{formatOddsAmerican(a.odds_a_american)}</span>
                    </div>
                    <p className="text-sm text-text-primary">{a.outcome_a}</p>
                    <p className="text-lg font-mono font-bold text-accent-yellow tabular-nums mt-1">{formatCurrency(a.stake_a)}</p>
                    {minBetWarningA && (
                      <p className="text-[10px] text-accent-red mt-1">Below ${a.book_a_min_bet} minimum bet</p>
                    )}
                  </div>
                  <div className="flex items-center text-text-muted text-xs font-mono">VS</div>
                  <div className={`flex-1 bg-bg-hover rounded-lg px-4 py-3 ${minBetWarningB ? "border border-accent-red/30" : ""}`}>
                    <div className="flex justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono text-text-muted uppercase">{a.book_b_display || a.book_b}</span>
                        <span className={`text-[9px] font-mono ${riskB.color}`}>{riskB.text}</span>
                      </div>
                      <span className="text-xs font-mono text-text-secondary">{formatOddsAmerican(a.odds_b_american)}</span>
                    </div>
                    <p className="text-sm text-text-primary">{a.outcome_b}</p>
                    <p className="text-lg font-mono font-bold text-accent-yellow tabular-nums mt-1">{formatCurrency(a.stake_b)}</p>
                    {minBetWarningB && (
                      <p className="text-[10px] text-accent-red mt-1">Below ${a.book_b_min_bet} minimum bet</p>
                    )}
                  </div>
                </div>

                {/* Footer info */}
                <div className="mt-2 flex items-center justify-between text-xs font-mono text-text-muted">
                  <div className="flex items-center gap-4">
                    <span>Allocated: {formatCurrency(a.allocated_amount)}</span>
                    <span>Safety: {a.rotation_score.toFixed(2)}</span>
                  </div>
                  {urgency === "dead" && (
                    <span className="text-accent-red font-semibold">Game may have started, verify before betting</span>
                  )}
                </div>
              </div>
              );
            })}
          </div>

          {plan.allocations.length === 0 && (
            <div className="text-center py-12 text-text-muted">
              <p className="font-medium">No allocations possible</p>
              <p className="text-sm mt-1">Run a scan first to find arb opportunities, then come back here.</p>
            </div>
          )}
        </>
      )}

      {!plan && (
        <div className="text-center py-16 text-text-muted">
          <div className="w-16 h-16 rounded-2xl bg-bg-hover border border-bg-border flex items-center justify-center mx-auto mb-4">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-text-muted">
              <line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
          </div>
          <p className="font-medium">Set your budget above</p>
          <p className="text-sm mt-1">The optimizer will spread your money across the best arbs while rotating sportsbooks for safety.</p>
        </div>
      )}
    </div>
  );
}