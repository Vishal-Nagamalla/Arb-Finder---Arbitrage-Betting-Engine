"use client";

import { useState } from "react";
import { api, CalcResponse, StakeInfo } from "@/lib/api";
import { formatCurrency, formatPercent, formatOddsAmerican } from "@/lib/utils";

// ─── Input Field ─────────────────────────────────────────────────────────────

function InputField({
  label,
  value,
  onChange,
  type = "text",
  placeholder,
  mono = false,
  small = false,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
  mono?: boolean;
  small?: boolean;
}) {
  return (
    <div>
      <label className="block text-[11px] font-mono text-text-muted uppercase tracking-wider mb-1.5">
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={`
          w-full bg-bg-hover border border-bg-border rounded-lg px-3 py-2.5
          text-text-primary placeholder-text-muted focus:outline-none
          focus:border-accent-green/50 focus:ring-1 focus:ring-accent-green/20
          transition-all
          ${mono ? "font-mono" : ""}
          ${small ? "text-sm" : ""}
        `}
      />
    </div>
  );
}

// ─── Result Display ──────────────────────────────────────────────────────────

function ResultCard({ result }: { result: CalcResponse }) {
  if (!result.is_arb) {
    return (
      <div className="bg-bg-card border border-accent-red/30 rounded-xl p-6 animate-fade-in">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-full bg-accent-redDim flex items-center justify-center">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-accent-red">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </div>
          <div>
            <p className="font-semibold text-accent-red">No Arbitrage Opportunity</p>
            <p className="text-sm text-text-muted">
              Combined implied probability:{" "}
              <span className="font-mono text-text-secondary">
                {(result.combined_implied_probability * 100).toFixed(2)}%
              </span>
            </p>
          </div>
        </div>
        <p className="text-sm text-text-secondary">
          For an arb to exist, the combined implied probability must be below 100%.
          These odds total {(result.combined_implied_probability * 100).toFixed(2)}%, meaning the
          books have priced this market with a {((result.combined_implied_probability - 1) * 100).toFixed(2)}% margin (their profit, your loss).
        </p>
      </div>
    );
  }

  const stakeEntries = Object.entries(result.stakes);

  return (
    <div className="bg-bg-card border border-accent-green/30 rounded-xl overflow-hidden animate-fade-in">
      {/* Header */}
      <div className="px-6 py-5 border-b border-bg-border flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-accent-greenDim flex items-center justify-center">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-accent-green">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
          <div>
            <p className="font-bold text-accent-green text-lg">Arbitrage Found</p>
            <p className="text-xs text-text-muted">Guaranteed profit regardless of outcome</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-3xl font-mono font-bold text-accent-green glow-green tabular-nums">
            {formatPercent(result.profit_percentage)}
          </p>
          <p className="text-xs font-mono text-text-muted">ROI</p>
        </div>
      </div>

      {/* Stake Breakdown */}
      <div className="px-6 py-4">
        <p className="text-[11px] font-mono text-text-muted uppercase tracking-wider mb-3">
          How to Bet
        </p>
        <div className="flex gap-3">
          {stakeEntries.map(([name, info]) => (
            <div key={name} className="flex-1 bg-bg-hover rounded-lg px-4 py-4">
              <p className="text-[10px] font-mono text-accent-blue uppercase mb-1">{info.book}</p>
              <p className="text-sm font-semibold text-text-primary mb-2">{name}</p>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-xs text-text-muted">Stake</span>
                  <span className="font-mono font-bold text-accent-yellow tabular-nums">
                    {formatCurrency(info.stake)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs text-text-muted">Odds</span>
                  <span className="font-mono text-sm text-text-secondary tabular-nums">
                    {info.odds_decimal.toFixed(2)} ({formatOddsAmerican(info.odds_american)})
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs text-text-muted">Returns</span>
                  <span className="font-mono text-sm text-accent-green tabular-nums">
                    {formatCurrency(info.potential_return)}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Summary Stats */}
      <div className="px-6 py-4 border-t border-bg-border">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-[10px] font-mono text-text-muted uppercase">Total Investment</p>
            <p className="text-lg font-mono font-bold text-text-primary tabular-nums">
              {formatCurrency(result.total_stake)}
            </p>
          </div>
          <div>
            <p className="text-[10px] font-mono text-text-muted uppercase">Guaranteed Return</p>
            <p className="text-lg font-mono font-bold text-accent-green tabular-nums">
              {formatCurrency(result.guaranteed_return)}
            </p>
          </div>
          <div>
            <p className="text-[10px] font-mono text-text-muted uppercase">Guaranteed Profit</p>
            <p className="text-lg font-mono font-bold text-accent-green glow-green tabular-nums">
              {formatCurrency(result.guaranteed_profit)}
            </p>
          </div>
          <div>
            <p className="text-[10px] font-mono text-text-muted uppercase">
              {result.profit_after_fees != null ? "After Fees" : "Arb Margin"}
            </p>
            <p
              className={`text-lg font-mono font-bold tabular-nums ${
                result.profit_after_fees != null && result.profit_after_fees < 0
                  ? "text-accent-red"
                  : "text-text-primary"
              }`}
            >
              {result.profit_after_fees != null
                ? formatCurrency(result.profit_after_fees)
                : `${(result.arb_margin * 100).toFixed(2)}%`}
            </p>
          </div>
        </div>
      </div>

      {/* Scenario Analysis */}
      <div className="px-6 py-4 border-t border-bg-border bg-bg-secondary">
        <p className="text-[11px] font-mono text-text-muted uppercase tracking-wider mb-3">
          Scenario Analysis
        </p>
        <div className="space-y-2">
          {result.scenarios.map((s, i) => (
            <div
              key={i}
              className="flex items-center justify-between bg-bg-hover rounded-lg px-4 py-2.5"
            >
              <span className="text-sm text-text-secondary">If {s.outcome}:</span>
              <div className="flex items-center gap-4">
                <span className="text-sm font-mono text-text-secondary tabular-nums">
                  Return {formatCurrency(s.return)}
                </span>
                <span className="text-sm font-mono font-bold text-accent-green tabular-nums">
                  {formatCurrency(s.profit)} profit
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Main Calculator Page ────────────────────────────────────────────────────

export default function CalculatorPage() {
  const [oddsFormat, setOddsFormat] = useState<"american" | "decimal">("american");
  const [oddsA, setOddsA] = useState("");
  const [oddsB, setOddsB] = useState("");
  const [oddsC, setOddsC] = useState("");
  const [bankroll, setBankroll] = useState("100");
  const [nameA, setNameA] = useState("");
  const [nameB, setNameB] = useState("");
  const [nameC, setNameC] = useState("");
  const [bookA, setBookA] = useState("");
  const [bookB, setBookB] = useState("");
  const [bookC, setBookC] = useState("");
  const [feePct, setFeePct] = useState("0");
  const [threeWay, setThreeWay] = useState(false);

  const [result, setResult] = useState<CalcResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const calculate = async () => {
    if (!oddsA || !oddsB) {
      setError("Enter odds for both outcomes");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const body: any = {
        odds_a: parseFloat(oddsA),
        odds_b: parseFloat(oddsB),
        odds_format: oddsFormat,
        bankroll: parseFloat(bankroll) || 100,
        outcome_a_name: nameA || "Team A",
        outcome_b_name: nameB || "Team B",
        book_a: bookA || "Book A",
        book_b: bookB || "Book B",
        fee_pct: parseFloat(feePct) || 0,
      };

      if (threeWay && oddsC) {
        body.odds_c = parseFloat(oddsC);
        body.outcome_c_name = nameC || "Draw";
        body.book_c = bookC || "Book C";
      }

      const res = await api.calculate(body);
      setResult(res);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const clear = () => {
    setOddsA("");
    setOddsB("");
    setOddsC("");
    setNameA("");
    setNameB("");
    setNameC("");
    setBookA("");
    setBookB("");
    setBookC("");
    setResult(null);
    setError(null);
  };

  return (
    <div className="px-8 py-6 max-w-[1100px]">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-xl font-bold text-text-primary">Manual Calculator</h2>
        <p className="text-sm text-text-muted mt-0.5">
          Input odds from any two sportsbooks to calculate your arb
        </p>
      </div>

      {/* Calculator Form */}
      <div className="bg-bg-card border border-bg-border rounded-xl p-6 mb-6">
        {/* Format Toggle + Options Row */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-text-muted uppercase">Odds Format:</span>
            <div className="flex bg-bg-hover rounded-lg overflow-hidden border border-bg-border">
              {(["american", "decimal"] as const).map((fmt) => (
                <button
                  key={fmt}
                  onClick={() => setOddsFormat(fmt)}
                  className={`
                    px-3 py-1.5 text-xs font-mono font-medium transition-all capitalize
                    ${oddsFormat === fmt ? "bg-accent-green text-bg-primary" : "text-text-secondary hover:text-text-primary"}
                  `}
                >
                  {fmt}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={() => {
              setThreeWay(!threeWay);
              setOddsC("");
              setNameC("");
              setBookC("");
            }}
            className={`
              px-3 py-1.5 rounded-lg text-xs font-medium border transition-all
              ${threeWay
                ? "bg-accent-blueDim border-accent-blue/30 text-accent-blue"
                : "bg-bg-hover border-bg-border text-text-secondary hover:text-text-primary"}
            `}
          >
            3-Way Market (Soccer)
          </button>
        </div>

        {/* Outcome Inputs */}
        <div className={`grid ${threeWay ? "grid-cols-3" : "grid-cols-2"} gap-4 mb-6`}>
          {/* Outcome A */}
          <div className="bg-bg-secondary rounded-xl p-4 border border-bg-border space-y-3">
            <p className="text-xs font-mono text-accent-blue font-semibold uppercase">Outcome A</p>
            <InputField label="Team / Outcome" value={nameA} onChange={setNameA} placeholder="e.g. Lakers" small />
            <InputField label="Sportsbook" value={bookA} onChange={setBookA} placeholder="e.g. FanDuel" small />
            <InputField
              label={`Odds (${oddsFormat})`}
              value={oddsA}
              onChange={setOddsA}
              placeholder={oddsFormat === "american" ? "e.g. +155" : "e.g. 2.55"}
              mono
            />
          </div>

          {/* Outcome B */}
          <div className="bg-bg-secondary rounded-xl p-4 border border-bg-border space-y-3">
            <p className="text-xs font-mono text-accent-blue font-semibold uppercase">Outcome B</p>
            <InputField label="Team / Outcome" value={nameB} onChange={setNameB} placeholder="e.g. Celtics" small />
            <InputField label="Sportsbook" value={bookB} onChange={setBookB} placeholder="e.g. DraftKings" small />
            <InputField
              label={`Odds (${oddsFormat})`}
              value={oddsB}
              onChange={setOddsB}
              placeholder={oddsFormat === "american" ? "e.g. -143" : "e.g. 1.70"}
              mono
            />
          </div>

          {/* Outcome C (3-way) */}
          {threeWay && (
            <div className="bg-bg-secondary rounded-xl p-4 border border-bg-border space-y-3">
              <p className="text-xs font-mono text-accent-blue font-semibold uppercase">Outcome C</p>
              <InputField label="Team / Outcome" value={nameC} onChange={setNameC} placeholder="e.g. Draw" small />
              <InputField label="Sportsbook" value={bookC} onChange={setBookC} placeholder="e.g. BetMGM" small />
              <InputField
                label={`Odds (${oddsFormat})`}
                value={oddsC}
                onChange={setOddsC}
                placeholder={oddsFormat === "american" ? "e.g. +260" : "e.g. 3.60"}
                mono
              />
            </div>
          )}
        </div>

        {/* Bankroll + Fee Row */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <InputField
            label="Total Bankroll ($)"
            value={bankroll}
            onChange={setBankroll}
            type="number"
            placeholder="100"
            mono
          />
          <InputField
            label="Platform Fee (%)"
            value={feePct}
            onChange={setFeePct}
            type="number"
            placeholder="0"
            mono
          />
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 px-4 py-3 rounded-lg bg-accent-redDim border border-accent-red/30 text-accent-red text-sm">
            {error}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-3">
          <button
            onClick={calculate}
            disabled={loading}
            className={`
              flex-1 py-3 rounded-lg font-semibold text-sm transition-all
              ${loading
                ? "bg-bg-hover text-text-muted cursor-wait"
                : "bg-accent-green text-bg-primary hover:brightness-110"}
            `}
          >
            {loading ? "Calculating..." : "Calculate Arb"}
          </button>
          <button
            onClick={clear}
            className="px-5 py-3 rounded-lg font-medium text-sm bg-bg-hover border border-bg-border text-text-secondary hover:text-text-primary transition-all"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Results */}
      {result && <ResultCard result={result} />}
    </div>
  );
}
