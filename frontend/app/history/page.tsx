"use client";

import { useState, useEffect, useCallback } from "react";
import { api, authFetch } from "@/lib/api";
import { formatCurrency, formatPercent, formatSportName, timeAgo } from "@/lib/utils";

// ─── Types ───────────────────────────────────────────────────────────────────

interface Bet {
  id: string;
  created_at: string;
  event_name: string;
  sport: string;
  outcome_a: string;
  book_a: string;
  stake_a: number;
  odds_a_american: number;
  outcome_b: string;
  book_b: string;
  stake_b: number;
  odds_b_american: number;
  total_stake: number;
  guaranteed_return: number;
  expected_profit: number;
  profit_percentage: number;
  actual_profit: number | null;
  status: string;
  winning_outcome: string | null;
  resolved_at: string | null;
  notes: string | null;
}

interface Stats {
  total_bets: number;
  pending: number;
  resolved: number;
  cancelled: number;
  total_profit: number;
  total_invested: number;
  avg_roi: number;
  best_profit: number;
  pending_profit: number;
  pending_stake: number;
  by_sport: { sport: string; count: number; profit: number }[];
  by_book: { book: string; count: number; profit: number }[];
}

// ─── Stat Card ───────────────────────────────────────────────────────────────

function StatCard({ label, value, color = "text-text-primary" }: {
  label: string; value: string; color?: string;
}) {
  return (
    <div className="bg-bg-card border border-bg-border rounded-xl px-5 py-4">
      <p className="text-[11px] font-mono text-text-muted uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-2xl font-mono font-bold tabular-nums ${color}`}>{value}</p>
    </div>
  );
}

// ─── Bet Row ─────────────────────────────────────────────────────────────────

function BetRow({ bet, onResolve, onCancel, onDelete }: {
  bet: Bet;
  onResolve: (id: string) => void;
  onCancel: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const statusColors: Record<string, string> = {
    pending: "bg-accent-yellowDim text-accent-yellow",
    resolved: "bg-accent-greenDim text-accent-green",
    cancelled: "bg-bg-hover text-text-muted",
  };

  return (
    <div className="bg-bg-card border border-bg-border rounded-xl px-5 py-4 card-hover">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className={`text-[10px] font-mono font-bold px-2 py-1 rounded-md ${statusColors[bet.status] || "bg-bg-hover text-text-muted"}`}>
            {bet.status.toUpperCase()}
          </span>
          <span className="text-[10px] font-mono px-2 py-1 rounded-md bg-accent-blueDim text-accent-blue">
            {formatSportName(bet.sport)}
          </span>
          <span className="text-sm font-semibold text-text-primary">{bet.event_name}</span>
        </div>
        <div className="text-right">
          <p className={`text-lg font-mono font-bold tabular-nums ${
            bet.status === "resolved" ? "text-accent-green glow-green" :
            bet.status === "cancelled" ? "text-text-muted" : "text-accent-yellow"
          }`}>
            {bet.status === "resolved"
              ? formatCurrency(bet.actual_profit ?? bet.expected_profit)
              : bet.status === "cancelled" ? "$0.00" : formatCurrency(bet.expected_profit)}
          </p>
          <p className="text-[10px] font-mono text-text-muted">
            {bet.status === "resolved" ? "actual profit" : bet.status === "cancelled" ? "cancelled" : "expected profit"}
          </p>
        </div>
      </div>

      {/* Bet details */}
      <div className="flex gap-3 mb-3">
        <div className="flex-1 bg-bg-hover rounded-lg px-3 py-2">
          <p className="text-[10px] font-mono text-text-muted uppercase">{bet.book_a}</p>
          <p className="text-sm text-text-primary">{bet.outcome_a}</p>
          <p className="font-mono font-bold text-accent-yellow text-sm tabular-nums">
            {formatCurrency(bet.stake_a)}
          </p>
        </div>
        <div className="flex items-center text-text-muted text-xs font-mono">VS</div>
        <div className="flex-1 bg-bg-hover rounded-lg px-3 py-2">
          <p className="text-[10px] font-mono text-text-muted uppercase">{bet.book_b}</p>
          <p className="text-sm text-text-primary">{bet.outcome_b}</p>
          <p className="font-mono font-bold text-accent-yellow text-sm tabular-nums">
            {formatCurrency(bet.stake_b)}
          </p>
        </div>
      </div>

      {/* Footer: meta + actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-xs text-text-muted font-mono">
          <span>ID: {bet.id}</span>
          <span>Staked: {formatCurrency(bet.total_stake)}</span>
          <span>{timeAgo(bet.created_at)}</span>
          {bet.winning_outcome && <span>Winner: {bet.winning_outcome}</span>}
          {bet.notes && <span className="text-text-secondary">Note: {bet.notes}</span>}
        </div>
        {bet.status === "pending" && (
          <div className="flex gap-2">
            <button
              onClick={() => onResolve(bet.id)}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-accent-greenDim text-accent-green border border-accent-green/30 hover:bg-accent-green/20 transition-all"
            >
              Resolve
            </button>
            <button
              onClick={() => onCancel(bet.id)}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-bg-hover text-text-secondary border border-bg-border hover:text-text-primary transition-all"
            >
              Cancel
            </button>
          </div>
        )}
        {bet.status !== "pending" && (
          <button
            onClick={() => onDelete(bet.id)}
            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-bg-hover text-text-muted border border-bg-border hover:text-accent-red hover:border-accent-red/30 transition-all"
          >
            Delete
          </button>
        )}
      </div>
    </div>
  );
}

// ─── Resolve Modal ───────────────────────────────────────────────────────────

function ResolveModal({ bet, onClose, onSubmit }: {
  bet: Bet;
  onClose: () => void;
  onSubmit: (winner: string, profit: number | null, notes: string) => void;
}) {
  const [winner, setWinner] = useState("");
  const [profit, setProfit] = useState(String(bet.expected_profit));
  const [notes, setNotes] = useState("");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-bg-card border border-bg-border rounded-2xl p-6 w-full max-w-md animate-fade-in" onClick={(e) => e.stopPropagation()}>
        <h3 className="font-bold text-text-primary mb-1">Resolve Bet</h3>
        <p className="text-sm text-text-muted mb-4">{bet.event_name}</p>

        <div className="space-y-3 mb-4">
          <div>
            <label className="block text-[11px] font-mono text-text-muted uppercase mb-1">Who won?</label>
            <div className="flex gap-2">
              {[bet.outcome_a, bet.outcome_b].map((o) => (
                <button
                  key={o}
                  onClick={() => setWinner(o)}
                  className={`flex-1 py-2.5 rounded-lg text-sm font-medium border transition-all ${
                    winner === o
                      ? "bg-accent-greenDim border-accent-green/30 text-accent-green"
                      : "bg-bg-hover border-bg-border text-text-secondary hover:text-text-primary"
                  }`}
                >
                  {o}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-mono text-text-muted uppercase mb-1">
              Actual Profit ($)
            </label>
            <input
              type="number"
              value={profit}
              onChange={(e) => setProfit(e.target.value)}
              className="w-full bg-bg-hover border border-bg-border rounded-lg px-3 py-2.5 font-mono text-text-primary focus:outline-none focus:border-accent-green/50 transition-all"
            />
            <p className="text-[10px] text-text-muted mt-1">
              Pre-filled with expected profit. Adjust if actual differs.
            </p>
          </div>

          <div>
            <label className="block text-[11px] font-mono text-text-muted uppercase mb-1">Notes (optional)</label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Withdrawal processing..."
              className="w-full bg-bg-hover border border-bg-border rounded-lg px-3 py-2.5 text-sm text-text-primary focus:outline-none focus:border-accent-green/50 transition-all"
            />
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => {
              if (!winner) return;
              onSubmit(winner, parseFloat(profit) || null, notes);
            }}
            disabled={!winner}
            className="flex-1 py-2.5 rounded-lg text-sm font-semibold bg-accent-green text-bg-primary disabled:opacity-30 hover:brightness-110 transition-all"
          >
            Confirm
          </button>
          <button
            onClick={onClose}
            className="px-5 py-2.5 rounded-lg text-sm font-medium bg-bg-hover border border-bg-border text-text-secondary hover:text-text-primary transition-all"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main History Page ───────────────────────────────────────────────────────

export default function HistoryPage() {
  const [bets, setBets] = useState<Bet[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [filter, setFilter] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [resolvingBet, setResolvingBet] = useState<Bet | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [betsRes, statsRes] = await Promise.all([
        authFetch(`/bets${filter ? `?status=${filter}` : ""}`).then((r) => r.json()),
        authFetch("/bets/stats").then((r) => r.json()),
      ]);
      setBets(betsRes.bets || []);
      setStats(statsRes);
    } catch (e) {
      console.error("Failed to load history:", e);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleResolve = async (winner: string, profit: number | null, notes: string) => {
    if (!resolvingBet) return;
    try {
      await authFetch(`/bets/${resolvingBet.id}/resolve`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ winning_outcome: winner, actual_profit: profit, notes }),
      });
      setResolvingBet(null);
      loadData();
    } catch (e) {
      console.error("Failed to resolve:", e);
    }
  };

  const handleCancel = async (id: string) => {
    try {
      await authFetch(`/bets/${id}/cancel`, { method: "PUT" });
      loadData();
    } catch (e) {
      console.error("Failed to cancel:", e);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await authFetch(`/bets/${id}`, { method: "DELETE" });
      loadData();
    } catch (e) {
      console.error("Failed to delete:", e);
    }
  };

  if (loading) {
    return (
      <div className="px-8 py-6 flex items-center justify-center h-64">
        <div className="animate-spin h-6 w-6 border-2 border-accent-green border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="px-8 py-6 max-w-[1400px]">
      {/* Resolve Modal */}
      {resolvingBet && (
        <ResolveModal
          bet={resolvingBet}
          onClose={() => setResolvingBet(null)}
          onSubmit={handleResolve}
        />
      )}

      {/* Header */}
      <div className="mb-6">
        <h2 className="text-xl font-bold text-text-primary">Bet History</h2>
        <p className="text-sm text-text-muted mt-0.5">Track your arb bets and cumulative profit</p>
      </div>

      {/* P&L Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <StatCard
            label="Total Profit"
            value={formatCurrency(stats.total_profit)}
            color={stats.total_profit >= 0 ? "text-accent-green" : "text-accent-red"}
          />
          <StatCard label="Total Invested" value={formatCurrency(stats.total_invested)} />
          <StatCard
            label="Avg ROI"
            value={formatPercent(stats.avg_roi)}
            color="text-accent-blue"
          />
          <StatCard label="Bets Resolved" value={String(stats.resolved)} />
          <StatCard
            label="Pending Profit"
            value={formatCurrency(stats.pending_profit)}
            color="text-accent-yellow"
          />
        </div>
      )}

      {/* Sport & Book breakdown */}
      {stats && (stats.by_sport.length > 0 || stats.by_book.length > 0) && (
        <div className="grid grid-cols-2 gap-4 mb-6">
          {stats.by_sport.length > 0 && (
            <div className="bg-bg-card border border-bg-border rounded-xl p-5">
              <p className="text-[11px] font-mono text-text-muted uppercase tracking-wider mb-3">
                Profit by Sport
              </p>
              <div className="space-y-2">
                {stats.by_sport.map((s) => (
                  <div key={s.sport} className="flex justify-between items-center">
                    <span className="text-sm text-text-secondary">{formatSportName(s.sport)}</span>
                    <span className={`font-mono font-bold text-sm tabular-nums ${
                      s.profit >= 0 ? "text-accent-green" : "text-accent-red"
                    }`}>
                      {formatCurrency(s.profit)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {stats.by_book.length > 0 && (
            <div className="bg-bg-card border border-bg-border rounded-xl p-5">
              <p className="text-[11px] font-mono text-text-muted uppercase tracking-wider mb-3">
                Profit by Sportsbook
              </p>
              <div className="space-y-2">
                {stats.by_book.map((b) => (
                  <div key={b.book} className="flex justify-between items-center">
                    <span className="text-sm text-text-secondary capitalize">{b.book}</span>
                    <span className={`font-mono font-bold text-sm tabular-nums ${
                      b.profit >= 0 ? "text-accent-green" : "text-accent-red"
                    }`}>
                      {formatCurrency(b.profit)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 mb-4">
        {[
          { label: "All", value: null },
          { label: "Pending", value: "pending" },
          { label: "Resolved", value: "resolved" },
          { label: "Cancelled", value: "cancelled" },
        ].map((tab) => (
          <button
            key={tab.label}
            onClick={() => setFilter(tab.value)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
              filter === tab.value
                ? "bg-accent-greenDim border-accent-green/30 text-accent-green"
                : "bg-bg-hover border-bg-border text-text-secondary hover:text-text-primary"
            }`}
          >
            {tab.label}
            {tab.value === null && stats ? ` (${stats.total_bets})` : ""}
            {tab.value === "pending" && stats ? ` (${stats.pending})` : ""}
            {tab.value === "resolved" && stats ? ` (${stats.resolved})` : ""}
          </button>
        ))}
      </div>

      {/* Bet List */}
      {bets.length > 0 ? (
        <div className="space-y-3 stagger-children">
          {bets.map((bet) => (
            <BetRow
              key={bet.id}
              bet={bet}
              onResolve={(id) => setResolvingBet(bets.find((b) => b.id === id) || null)}
              onCancel={handleCancel}
              onDelete={handleDelete}
            />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-16 h-16 rounded-2xl bg-bg-hover border border-bg-border flex items-center justify-center mb-4">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-text-muted">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
            </svg>
          </div>
          <p className="text-text-secondary font-medium mb-1">No bets tracked yet</p>
          <p className="text-sm text-text-muted max-w-sm">
            When you find an arb on the Live Scanner, click "Track Bet" to add it here and monitor your profit over time.
          </p>
        </div>
      )}
    </div>
  );
}