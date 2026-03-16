"use client";

import { useState, useEffect } from "react";
import { api, authFetch, Settings, AutoScanStatus } from "@/lib/api";
import { formatSportName } from "@/lib/utils";

// ─── Toggle Chip ─────────────────────────────────────────────────────────────

function ToggleChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`
        px-3 py-1.5 rounded-lg text-xs font-medium border transition-all
        ${
          active
            ? "bg-accent-greenDim border-accent-green/30 text-accent-green"
            : "bg-bg-hover border-bg-border text-text-muted hover:text-text-secondary"
        }
      `}
    >
      {label}
    </button>
  );
}

// ─── Section Card ────────────────────────────────────────────────────────────

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-bg-card border border-bg-border rounded-xl p-6">
      <h3 className="font-semibold text-text-primary mb-1">{title}</h3>
      {description && <p className="text-sm text-text-muted mb-4">{description}</p>}
      {children}
    </div>
  );
}

// ─── All available sports ────────────────────────────────────────────────────

const ALL_SPORTS = [
  "basketball_nba",
  "americanfootball_nfl",
  "baseball_mlb",
  "icehockey_nhl",
  "soccer_epl",
  "soccer_usa_mls",
  "basketball_ncaab",
  "americanfootball_ncaaf",
  "mma_mixed_martial_arts",
];

const ALL_BOOKS = [
  "fanduel",
  "draftkings",
  "betmgm",
  "caesars",
  "espnbet",
  "fanatics",
  "hardrockbet",
  "betrivers",
  "pointsbet",
  "bet365",
  "unibet",
];

// ─── Settings Page ───────────────────────────────────────────────────────────

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [autoScan, setAutoScan] = useState<AutoScanStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  // Form state
  const [bankroll, setBankroll] = useState("1000");
  const [minProfit, setMinProfit] = useState("0.5");
  const [maxProfit, setMaxProfit] = useState("20");
  const [scanInterval, setScanInterval] = useState("120");
  const [selectedSports, setSelectedSports] = useState<string[]>([]);
  const [selectedBooks, setSelectedBooks] = useState<string[]>([]);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const [s, a] = await Promise.all([api.getSettings(), api.getAutoScanStatus()]);
      setSettings(s);
      setAutoScan(a);
      setBankroll(String(s.bankroll));
      setMinProfit(String(s.min_profit_pct));
      setMaxProfit(String(s.max_profit_pct));
      setScanInterval(String(s.auto_scan_interval));
      setSelectedSports(s.scan_sports);
      setSelectedBooks(s.enabled_books);
    } catch (e) {
      console.error("Failed to load settings:", e);
    } finally {
      setLoading(false);
    }
  };

  const save = async () => {
    setSaving(true);
    setMessage(null);
    try {
      await api.updateSettings({
        bankroll: parseFloat(bankroll) || 1000,
        min_profit_pct: parseFloat(minProfit) || 0.5,
        max_profit_pct: parseFloat(maxProfit) || 20,
        auto_scan_interval: parseInt(scanInterval) || 120,
        scan_sports: selectedSports,
        enabled_books: selectedBooks,
      });
      setMessage("Settings saved successfully");
      setTimeout(() => setMessage(null), 3000);
    } catch (e: any) {
      setMessage(`Error: ${e.message}`);
    } finally {
      setSaving(false);
    }
  };

  const toggleSport = (sport: string) => {
    setSelectedSports((prev) =>
      prev.includes(sport) ? prev.filter((s) => s !== sport) : [...prev, sport]
    );
  };

  const toggleBook = (book: string) => {
    setSelectedBooks((prev) =>
      prev.includes(book) ? prev.filter((b) => b !== book) : [...prev, book]
    );
  };

  if (loading) {
    return (
      <div className="px-8 py-6 flex items-center justify-center h-64">
        <div className="animate-spin h-6 w-6 border-2 border-accent-green border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="px-8 py-6 max-w-[900px]">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-text-primary">Settings</h2>
          <p className="text-sm text-text-muted mt-0.5">Configure your scanning preferences</p>
        </div>
        <div className="flex items-center gap-3">
          {message && (
            <span
              className={`text-sm font-medium animate-fade-in ${
                message.startsWith("Error") ? "text-accent-red" : "text-accent-green"
              }`}
            >
              {message}
            </span>
          )}
          <button
            onClick={save}
            disabled={saving}
            className="px-5 py-2.5 rounded-lg text-sm font-semibold bg-accent-green text-bg-primary hover:brightness-110 transition-all disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {/* General */}
        <Section title="General" description="Core configuration for the arb engine">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-[11px] font-mono text-text-muted uppercase tracking-wider mb-1.5">
                Bankroll ($)
              </label>
              <input
                type="number"
                value={bankroll}
                onChange={(e) => setBankroll(e.target.value)}
                className="w-full bg-bg-hover border border-bg-border rounded-lg px-3 py-2.5 font-mono text-text-primary focus:outline-none focus:border-accent-green/50 transition-all"
              />
            </div>
            <div>
              <label className="block text-[11px] font-mono text-text-muted uppercase tracking-wider mb-1.5">
                Auto-Scan Interval (seconds)
              </label>
              <input
                type="number"
                value={scanInterval}
                onChange={(e) => setScanInterval(e.target.value)}
                min="30"
                className="w-full bg-bg-hover border border-bg-border rounded-lg px-3 py-2.5 font-mono text-text-primary focus:outline-none focus:border-accent-green/50 transition-all"
              />
            </div>
            <div>
              <label className="block text-[11px] font-mono text-text-muted uppercase tracking-wider mb-1.5">
                Min Profit % to Flag
              </label>
              <input
                type="number"
                value={minProfit}
                onChange={(e) => setMinProfit(e.target.value)}
                step="0.1"
                className="w-full bg-bg-hover border border-bg-border rounded-lg px-3 py-2.5 font-mono text-text-primary focus:outline-none focus:border-accent-green/50 transition-all"
              />
            </div>
            <div>
              <label className="block text-[11px] font-mono text-text-muted uppercase tracking-wider mb-1.5">
                Max Profit % (filter errors)
              </label>
              <input
                type="number"
                value={maxProfit}
                onChange={(e) => setMaxProfit(e.target.value)}
                step="1"
                className="w-full bg-bg-hover border border-bg-border rounded-lg px-3 py-2.5 font-mono text-text-primary focus:outline-none focus:border-accent-green/50 transition-all"
              />
            </div>
          </div>
        </Section>

        {/* Sports */}
        <Section
          title="Sports"
          description="Select which sports to scan. More sports = more API requests per scan."
        >
          <div className="flex flex-wrap gap-2">
            {ALL_SPORTS.map((sport) => (
              <ToggleChip
                key={sport}
                label={formatSportName(sport)}
                active={selectedSports.includes(sport)}
                onClick={() => toggleSport(sport)}
              />
            ))}
          </div>
          <p className="text-xs text-text-muted mt-3">
            {selectedSports.length} sports selected, uses ~{selectedSports.length} API requests per scan
          </p>
        </Section>

        {/* Sportsbooks */}
        <Section
          title="Sportsbooks"
          description="Select which books to compare. More books = more cross-book combinations to check."
        >
          <div className="flex flex-wrap gap-2">
            {ALL_BOOKS.map((book) => (
              <ToggleChip
                key={book}
                label={book.charAt(0).toUpperCase() + book.slice(1).replace(/_/g, " ")}
                active={selectedBooks.includes(book)}
                onClick={() => toggleBook(book)}
              />
            ))}
          </div>
          <p className="text-xs text-text-muted mt-3">{selectedBooks.length} sportsbooks enabled</p>
        </Section>

        {/* API Keys */}
        <Section title="API Keys" description="Add multiple Odds API keys for rotation. Each key gives 500 requests/month.">
          <div className="space-y-3 mb-4">
            {(settings as any)?.api_keys?.keys?.map((k: any, i: number) => (
              <div key={i} className="flex items-center justify-between bg-bg-hover rounded-lg px-4 py-3">
                <div className="flex items-center gap-3">
                  <span className={`w-2 h-2 rounded-full ${k.active ? "bg-accent-green pulse-green" : k.exhausted ? "bg-accent-red" : "bg-text-muted"}`} />
                  <span className="font-mono text-sm text-text-secondary">{k.key_masked}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-xs font-mono text-text-muted">
                    {k.remaining != null ? `${k.remaining} left` : "Untested"}
                  </span>
                  {k.exhausted && (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent-redDim text-accent-red">
                      EXHAUSTED
                    </span>
                  )}
                  {k.active && (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent-greenDim text-accent-green">
                      ACTIVE
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Paste a new API key..."
              id="newKeyInput"
              className="flex-1 bg-bg-hover border border-bg-border rounded-lg px-3 py-2.5 font-mono text-sm text-text-primary focus:outline-none focus:border-accent-green/50 transition-all"
            />
            <button
              onClick={async () => {
                const input = document.getElementById("newKeyInput") as HTMLInputElement;
                const key = input?.value?.trim();
                if (!key) return;
                try {
                  await authFetch("/keys", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ api_key: key }),
                  });
                  input.value = "";
                  loadSettings();
                } catch (e) {
                  console.error(e);
                }
              }}
              className="px-4 py-2.5 rounded-lg text-sm font-semibold bg-accent-green text-bg-primary hover:brightness-110 transition-all"
            >
              Add Key
            </button>
          </div>
          <p className="text-xs text-text-muted mt-2">
            Total: {(settings as any)?.api_keys?.total_remaining ?? 0} requests remaining across {(settings as any)?.api_keys?.total_keys ?? 0} key(s)
          </p>
        </Section>

        {/* Notifications */}
        <Section title="Notifications" description="Get alerted when high-value arbs appear. Email is free, Pushover is optional ($5).">
          <div className="grid grid-cols-3 gap-4 mb-3">
            <div className="bg-bg-hover rounded-lg px-4 py-3">
              <p className="text-[10px] font-mono text-text-muted uppercase">Email (Free)</p>
              <p className={`font-mono font-bold ${(settings as any)?.notifications?.email_configured ? "text-accent-green" : "text-text-muted"}`}>
                {(settings as any)?.notifications?.email_configured
                  ? (settings as any)?.notifications?.email_address || "Active"
                  : "Not Set Up"}
              </p>
            </div>
            <div className="bg-bg-hover rounded-lg px-4 py-3">
              <p className="text-[10px] font-mono text-text-muted uppercase">Pushover (Optional)</p>
              <p className={`font-mono font-bold ${(settings as any)?.notifications?.pushover_configured ? "text-accent-green" : "text-text-muted"}`}>
                {(settings as any)?.notifications?.pushover_configured ? "Active" : "Not Set Up"}
              </p>
            </div>
            <div className="bg-bg-hover rounded-lg px-4 py-3">
              <p className="text-[10px] font-mono text-text-muted uppercase">Min Profit to Notify</p>
              <p className="font-mono font-bold text-text-primary">
                ${(settings as any)?.notifications?.min_profit_to_notify ?? "25.00"}
              </p>
            </div>
          </div>
          <p className="text-xs text-text-muted">
            For free email alerts, add NOTIFY_EMAIL and NOTIFY_EMAIL_PASSWORD (Gmail app password) to your .env file. Set MIN_PROFIT_TO_NOTIFY to control the threshold.
          </p>
        </Section>
      </div>
    </div>
  );
}