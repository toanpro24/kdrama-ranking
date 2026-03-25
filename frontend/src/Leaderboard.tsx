import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { fetchLeaderboard } from "./api";
import type { LeaderboardEntry } from "./types";
import { TIERS, GENRES } from "./constants";
import "./index.css";

const SORT_OPTIONS = [
  { value: "score", label: "Avg Score" },
  { value: "lists", label: "Most Listed" },
  { value: "top", label: "Most Top-Tier" },
] as const;

const TIER_COLORS: Record<string, string> = {};
TIERS.forEach((t) => { TIER_COLORS[t.id] = t.color; });

function ScoreBar({ score }: { score: number }) {
  // Score ranges 0-6 (splus=6), show as percentage
  const pct = Math.min((score / 6) * 100, 100);
  const color = score >= 5 ? "#E500A4" : score >= 4 ? "#FF2942" : score >= 3 ? "#FF7B3A" : score >= 2 ? "#FFC53A" : "#3AD9A0";
  return (
    <div className="lb-score-bar-bg">
      <div className="lb-score-bar-fill" style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

function TierBadges({ tierCounts }: { tierCounts: Record<string, number> }) {
  return (
    <div className="lb-tier-badges">
      {TIERS.map((t) => {
        const count = tierCounts[t.id] || 0;
        if (!count) return null;
        return (
          <span key={t.id} className="lb-tier-badge" style={{ borderColor: t.color, color: t.color }}>
            {t.label} x{count}
          </span>
        );
      })}
    </div>
  );
}

export default function Leaderboard() {
  const navigate = useNavigate();
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [totalUsers, setTotalUsers] = useState(0);
  const [loading, setLoading] = useState(true);
  const [sort, setSort] = useState<"score" | "lists" | "top">("score");
  const [genre, setGenre] = useState("All");

  useEffect(() => {
    setLoading(true);
    fetchLeaderboard(sort, genre).then((data) => {
      setEntries(data.entries);
      setTotalUsers(data.totalUsers);
      setLoading(false);
    });
  }, [sort, genre]);

  const topThree = useMemo(() => entries.slice(0, 3), [entries]);
  const rest = useMemo(() => entries.slice(3), [entries]);

  return (
    <div className="detail-page">
      <div className="detail-top-bar">
        <button className="detail-back" onClick={() => navigate("/")}>← Back to Tier List</button>
      </div>

      <h1 className="lb-title">Global Leaderboard</h1>
      <p className="lb-subtitle">
        Most popular actresses across {totalUsers} public tier list{totalUsers !== 1 ? "s" : ""}
      </p>

      <div className="lb-controls">
        <div className="lb-sort-group">
          <span className="lb-sort-label">Sort by:</span>
          {SORT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              className={`lb-sort-btn ${sort === opt.value ? "active" : ""}`}
              onClick={() => setSort(opt.value)}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <div className="lb-genre-group">
          {GENRES.map((g) => (
            <button
              key={g}
              className={`genre-pill ${genre === g ? "active" : ""}`}
              onClick={() => setGenre(g)}
            >
              {g}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="loading">Loading leaderboard...</div>
      ) : entries.length === 0 ? (
        <div className="settings-empty">
          <h2>No public tier lists yet</h2>
          <p style={{ color: "#666", marginTop: 8 }}>
            Set your tier list visibility to "Public" in Settings to appear on the leaderboard.
          </p>
        </div>
      ) : (
        <>
          {/* Top 3 Podium */}
          {topThree.length > 0 && (
            <div className="lb-podium">
              {topThree.map((entry, i) => (
                <div
                  key={entry.actressId}
                  className={`lb-podium-card lb-podium-${i + 1}`}
                  onClick={() => navigate(`/actress/${entry.actressId}`)}
                >
                  <span className="lb-podium-rank">#{entry.rank}</span>
                  {entry.image ? (
                    <img className="lb-podium-img" src={entry.image} alt={entry.name} />
                  ) : (
                    <div className="lb-podium-placeholder">{entry.name.charAt(0)}</div>
                  )}
                  <span className="lb-podium-name">{entry.name}</span>
                  <span className="lb-podium-known">{entry.known}</span>
                  <div className="lb-podium-stats">
                    <span className="lb-podium-score">{entry.avgScore.toFixed(1)}</span>
                    <span className="lb-podium-lists">{entry.totalLists} list{entry.totalLists !== 1 ? "s" : ""}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Full Table */}
          {rest.length > 0 && (
            <div className="lb-table">
              <div className="lb-table-header">
                <span className="lb-col-rank">#</span>
                <span className="lb-col-name">Actress</span>
                <span className="lb-col-score">Score</span>
                <span className="lb-col-lists">Lists</span>
                <span className="lb-col-tiers">Tier Breakdown</span>
              </div>
              {rest.map((entry) => (
                <div
                  key={entry.actressId}
                  className="lb-table-row"
                  onClick={() => navigate(`/actress/${entry.actressId}`)}
                >
                  <span className="lb-col-rank lb-rank-num">{entry.rank}</span>
                  <div className="lb-col-name lb-actress-info">
                    {entry.image ? (
                      <img className="lb-row-img" src={entry.image} alt={entry.name} />
                    ) : (
                      <div className="lb-row-placeholder">{entry.name.charAt(0)}</div>
                    )}
                    <div>
                      <span className="lb-row-name">{entry.name}</span>
                      <span className="lb-row-genre">{entry.genre}</span>
                    </div>
                  </div>
                  <div className="lb-col-score">
                    <span className="lb-score-num">{entry.avgScore.toFixed(1)}</span>
                    <ScoreBar score={entry.avgScore} />
                  </div>
                  <span className="lb-col-lists">{entry.totalLists}</span>
                  <div className="lb-col-tiers">
                    <TierBadges tierCounts={entry.tierCounts} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
