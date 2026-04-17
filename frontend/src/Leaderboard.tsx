import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { fetchLeaderboard, fetchTrending, fetchPublicUsers, followUser, unfollowUser } from "./api";
import type { LeaderboardEntry, TrendingEntry, PublicUser } from "./types";
import { useAuth } from "./AuthContext";
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
  // Score ranges 0-10 (splus=10), show as percentage
  const pct = Math.min((score / 10) * 100, 100);
  const color = score >= 8 ? "#E500A4" : score >= 5 ? "#FF2942" : score >= 3 ? "#FF7B3A" : score >= 2 ? "#FFC53A" : "#3AD9A0";
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
  const { user } = useAuth();
  const [tab, setTab] = useState<"leaderboard" | "trending" | "users">("leaderboard");
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [trendingEntries, setTrendingEntries] = useState<TrendingEntry[]>([]);
  const [publicUsers, setPublicUsers] = useState<PublicUser[]>([]);
  const [totalUsers, setTotalUsers] = useState(0);
  const [loading, setLoading] = useState(true);
  const [sort, setSort] = useState<"score" | "lists" | "top">("score");
  const [genre, setGenre] = useState("All");

  useEffect(() => {
    if (tab === "leaderboard") {
      setLoading(true);
      fetchLeaderboard(sort, genre).then((data) => {
        setEntries(data.entries);
        setTotalUsers(data.totalUsers);
        setLoading(false);
      });
    } else if (tab === "trending") {
      setLoading(true);
      fetchTrending().then((data) => {
        setTrendingEntries(data.entries);
        setTotalUsers(data.totalUsers);
        setLoading(false);
      });
    } else {
      setLoading(true);
      fetchPublicUsers().then((data) => {
        setPublicUsers(data);
        setLoading(false);
      });
    }
  }, [sort, genre, tab]);

  const handleToggleFollow = async (u: PublicUser) => {
    if (!user) {
      navigate("/");
      return;
    }
    const currentlyFollowing = u.isFollowing;
    setPublicUsers((prev) => prev.map((p) => p.userId === u.userId ? { ...p, isFollowing: !currentlyFollowing } : p));
    const ok = currentlyFollowing ? await unfollowUser(u.shareSlug) : await followUser(u.shareSlug);
    if (!ok) {
      setPublicUsers((prev) => prev.map((p) => p.userId === u.userId ? { ...p, isFollowing: currentlyFollowing } : p));
    }
  };

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

      {/* Tab switcher */}
      <div className="lb-tabs">
        <button className={`lb-tab ${tab === "leaderboard" ? "active" : ""}`} onClick={() => setTab("leaderboard")}>
          Rankings
        </button>
        <button className={`lb-tab ${tab === "trending" ? "active" : ""}`} onClick={() => setTab("trending")}>
          Trending
        </button>
        <button className={`lb-tab ${tab === "users" ? "active" : ""}`} onClick={() => setTab("users")}>
          Users
        </button>
      </div>

      {tab === "leaderboard" && (
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
      )}

      {loading ? (
        <div className="loading">Loading {tab === "trending" ? "trending" : tab === "users" ? "users" : "leaderboard"}...</div>
      ) : tab === "users" ? (
        publicUsers.length === 0 ? (
          <div className="settings-empty">
            <h2>No public users yet</h2>
            <p style={{ color: "#666", marginTop: 8 }}>
              Users who set their tier list to Public will show up here. Be the first by changing your visibility in Settings.
            </p>
          </div>
        ) : (
          <div className="fw-list">
            {publicUsers.map((u) => (
              <div key={u.userId} className="fw-card">
                <div className="fw-card-main" onClick={() => navigate(`/tier-list/${u.shareSlug}`)}>
                  {u.picture ? (
                    <img className="fw-avatar" src={u.picture} alt="" referrerPolicy="no-referrer" />
                  ) : (
                    <div className="fw-avatar-placeholder">{(u.displayName || "?").charAt(0)}</div>
                  )}
                  <div className="fw-info">
                    <span className="fw-name">{u.displayName || "User"}</span>
                    {u.bio && <span className="fw-bio">{u.bio}</span>}
                    <span className="fw-meta">{u.rankedCount} ranked</span>
                  </div>
                </div>
                <div className="fw-actions">
                  <button
                    className={`follow-btn ${u.isFollowing ? "following" : ""}`}
                    onClick={(e) => { e.stopPropagation(); handleToggleFollow(u); }}
                  >
                    {u.isFollowing ? "Following" : "Follow"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )
      ) : tab === "trending" ? (
        trendingEntries.length === 0 ? (
          <div className="settings-empty">
            <h2>No trending data yet</h2>
            <p style={{ color: "#666", marginTop: 8 }}>
              Trending actresses will appear here once more users make their tier lists public.
            </p>
          </div>
        ) : (
          <div className="lb-trending">
            {trendingEntries.map((entry) => (
              <div
                key={entry.actressId}
                className="lb-trending-card"
                onClick={() => navigate(`/actress/${entry.actressId}`)}
              >
                <span className="lb-trending-rank">#{entry.rank}</span>
                {entry.image ? (
                  <img className="lb-trending-img" src={entry.image} alt={entry.name} referrerPolicy="no-referrer" />
                ) : (
                  <div className="lb-trending-placeholder">{entry.name.charAt(0)}</div>
                )}
                <div className="lb-trending-info">
                  <span className="lb-trending-name">{entry.name}</span>
                  <span className="lb-trending-known">{entry.known}</span>
                </div>
                <div className="lb-trending-stats">
                  <span className="lb-trending-score">{entry.trendScore}</span>
                  <span className="lb-trending-meta">{entry.userCount} list{entry.userCount !== 1 ? "s" : ""} · {entry.avgScore.toFixed(1)} avg</span>
                </div>
              </div>
            ))}
          </div>
        )
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
