import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import type { Stats } from "./types";
import { fetchStats } from "./api";
import { TIERS } from "./constants";
import { useActresses } from "./ActressContext";
import "./index.css";

export default function StatsPage() {
  const navigate = useNavigate();
  const { actresses, loading } = useActresses();
  const [stats, setStats] = useState<Stats | null>(null);

  const loadStats = useCallback(async () => {
    const data = await fetchStats();
    setStats(data);
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  if (loading || !stats) return <div className="loading-page"><div className="loading-spinner" /><span className="loading-text">Loading stats...</span></div>;

  return (
    <div className="detail-page">
      <button className="detail-back" onClick={() => navigate("/")}>&#x2190; Back to Tier List</button>
      <main className="main-content">
        <section className="stats-page">
          <h2 className="stats-page-title">Your Ranking Breakdown</h2>
          <div className="stats-grid">
            <div className="stats-card">
              <h3 className="stats-card-title">Tier Distribution</h3>
              {TIERS.map((t) => {
                const count = stats.tierCounts[t.id] || 0;
                const pct = stats.ranked > 0 ? (count / stats.ranked) * 100 : 0;
                return (
                  <div key={t.id} className="dist-row">
                    <span className="dist-label" style={{ color: t.color }}>{t.label}</span>
                    <div className="dist-bar-bg">
                      <div className="dist-bar-fill" style={{ width: `${Math.max(pct, 2)}%`, background: t.color }} />
                    </div>
                    <span className="dist-num">{count}</span>
                  </div>
                );
              })}
            </div>
            <div className="stats-card">
              <h3 className="stats-card-title">Genre Breakdown</h3>
              {Object.entries(stats.genreCounts).sort((a, b) => b[1] - a[1]).map(([genre, count]) => {
                const pct = (count / stats.total) * 100;
                return (
                  <div key={genre} className="dist-row">
                    <span className="dist-label">{genre}</span>
                    <div className="dist-bar-bg">
                      <div className="dist-bar-fill" style={{ width: `${Math.max(pct, 2)}%`, background: "linear-gradient(90deg, #FF2942, #FF7B3A)" }} />
                    </div>
                    <span className="dist-num">{count}</span>
                  </div>
                );
              })}
            </div>
            <div className="stats-card" style={{ gridColumn: "1 / -1" }}>
              <h3 className="stats-card-title">Roster by Tier</h3>
              {TIERS.map((t) => {
                const members = actresses.filter((a) => a.tier === t.id);
                return (
                  <div key={t.id} style={{ marginBottom: 20 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                      <span className="roster-badge" style={{ background: t.color }}>{t.label}</span>
                      <span style={{ fontSize: 13, color: "#888" }}>{members.length} actress{members.length !== 1 ? "es" : ""}</span>
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                      {members.length === 0 && <span style={{ fontSize: 13, color: "#444", fontStyle: "italic" }}>Empty</span>}
                      {members.map((a) => (
                        <span key={a._id} className="roster-chip" style={{ borderColor: t.color + "66" }}>
                          <span style={{ color: t.color, marginRight: 4 }}>●</span>{a.name}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
