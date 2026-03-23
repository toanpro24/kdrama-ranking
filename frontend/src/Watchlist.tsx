import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import type { WatchStatus } from "./types";
import { fetchWatchlist, updateWatchStatus, rateDrama } from "./api";
import type { WatchlistItem } from "./api";
import { useAuth } from "./AuthContext";
import "./index.css";

const STATUS_TABS: { key: string; label: string }[] = [
  { key: "all", label: "All" },
  { key: "watching", label: "Watching" },
  { key: "plan_to_watch", label: "Plan to Watch" },
  { key: "watched", label: "Watched" },
  { key: "dropped", label: "Dropped" },
];

const STATUS_LABELS: Record<string, string> = {
  watching: "Watching",
  plan_to_watch: "Plan to Watch",
  watched: "Watched",
  dropped: "Dropped",
};

export default function Watchlist() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }
    fetchWatchlist()
      .then((data) => { setItems(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [user]);

  const filtered = useMemo(() => {
    let list = items;
    if (filter !== "all") list = list.filter((i) => i.watchStatus === filter);
    if (search) {
      const q = search.toLowerCase();
      list = list.filter((i) =>
        i.title.toLowerCase().includes(q) ||
        i.cast.some((c) => c.actressName.toLowerCase().includes(q))
      );
    }
    return list;
  }, [items, filter, search]);

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: items.length };
    for (const i of items) {
      c[i.watchStatus] = (c[i.watchStatus] || 0) + 1;
    }
    return c;
  }, [items]);

  function handleStatusChange(item: WatchlistItem, newStatus: WatchStatus) {
    if (!user) return;
    if (newStatus === null) {
      setItems((prev) => prev.filter((i) => i.title !== item.title));
    } else {
      setItems((prev) =>
        prev.map((i) => i.title === item.title ? { ...i, watchStatus: newStatus } : i)
      );
    }
    updateWatchStatus(item.actressId, item.title, newStatus);
  }

  async function handleRating(item: WatchlistItem, star: number) {
    if (!user) return;
    const newRating = star === item.rating ? null : star;
    const ok = await rateDrama(item.actressId, item.title, newRating);
    if (ok) {
      setItems((prev) =>
        prev.map((i) => i.title === item.title ? { ...i, rating: newRating } : i)
      );
    }
  }

  if (loading) return <div className="loading-page"><div className="loading-spinner" /><span className="loading-text">Loading watchlist...</span></div>;

  if (!user) {
    return (
      <div className="detail-page">
        <button className="detail-back" onClick={() => navigate(-1)}>&#x2190; Back</button>
        <div className="error-page">
          <span className="error-icon">!</span>
          <span className="error-message">Sign in to track your watch list</span>
        </div>
      </div>
    );
  }

  return (
    <div className="detail-page">
      <button className="detail-back" onClick={() => navigate(-1)}>&#x2190; Back</button>
      <h1 className="recs-title">My Watch List</h1>
      <p className="recs-subtitle">Track what you're watching, planning, and have finished</p>

      <div className="watchlist-search-wrap">
        <span className="search-icon">⌕</span>
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search dramas or actresses..." className="search-input" aria-label="Search watchlist" />
      </div>

      <div className="recs-filters">
        {STATUS_TABS.map((t) => (
          <button
            key={t.key}
            className={`sort-pill ${filter === t.key ? "active" : ""}`}
            onClick={() => setFilter(t.key)}
          >
            {t.label} {counts[t.key] ? `(${counts[t.key]})` : ""}
          </button>
        ))}
      </div>

      <div className="recs-grid">
        {filtered.map((item) => (
          <div
            key={item.title}
            className="recs-card"
            onClick={() => navigate(`/drama/${encodeURIComponent(item.title)}`)}
          >
            {item.poster ? (
              <img
                className="recs-poster"
                src={item.poster}
                alt={item.title}
                loading="lazy"
                referrerPolicy="no-referrer"
                onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
              />
            ) : (
              <div className="recs-poster-placeholder">
                <span>{item.title.charAt(0)}</span>
              </div>
            )}
            <div className="recs-info">
              <span className="recs-drama-title">{item.title}</span>
              <span className="recs-drama-year">{item.year}</span>
              <span className="recs-drama-actress">
                {item.cast.map((c) => c.actressName).join(", ")}
              </span>
              <span className={`watchlist-status-badge ws-badge-${item.watchStatus}`}>
                {STATUS_LABELS[item.watchStatus] || item.watchStatus}
              </span>
              <div className="drama-rating watchlist-rating" onClick={(e) => e.stopPropagation()}>
                {[...Array(10)].map((_, s) => (
                  <span
                    key={s}
                    className={`rating-star ${(item.rating || 0) > s ? "filled" : ""}`}
                    onClick={() => handleRating(item, s + 1)}
                  >
                    ★
                  </span>
                ))}
                {item.rating && <span className="rating-value">{item.rating}/10</span>}
              </div>
              <div className="watch-status-row watchlist-actions" onClick={(e) => e.stopPropagation()}>
                {(["watched", "watching", "plan_to_watch", "dropped"] as WatchStatus[]).map((ws) => (
                  <button
                    key={ws}
                    className={`watch-btn ${item.watchStatus === ws ? "active" : ""} ws-${ws}`}
                    onClick={() => handleStatusChange(item, item.watchStatus === ws ? null : ws)}
                  >
                    {ws === "watched" ? "Watched" : ws === "watching" ? "Watching" : ws === "plan_to_watch" ? "Plan" : "Dropped"}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <div className="recs-empty">
            {items.length === 0
              ? "Your watch list is empty. Visit a drama page and mark it as watching or plan to watch!"
              : "No dramas in this category."}
          </div>
        )}
      </div>
    </div>
  );
}
