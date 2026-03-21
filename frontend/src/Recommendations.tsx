import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { TIER_WEIGHT } from "./constants";
import { useActresses } from "./ActressContext";
import "./index.css";

interface Recommendation {
  dramaTitle: string;
  year: number;
  poster: string | null;
  actress: { id: string; name: string; role: string; tier: string | null };
  reasons: string[];
  score: number;
}

export default function Recommendations() {
  const navigate = useNavigate();
  const { actresses } = useActresses();
  const [filter, setFilter] = useState<"all" | "unwatched" | "top">("all");

  const { recommendations, watchedTitles, genreProfile } = useMemo(() => {
    const watched = new Set<string>();
    const ratedHigh = new Set<string>(); // dramas rated 7+
    const genreCounts: Record<string, number> = {};
    const likedActresses = new Set<string>(); // tier S+ / S / A or rated dramas 8+

    // Build user profile
    for (const a of actresses) {
      if (a.tier && TIER_WEIGHT[a.tier] >= 4) {
        likedActresses.add(a._id);
      }
      genreCounts[a.genre] = (genreCounts[a.genre] || 0) + 1;
      for (const d of a.dramas || []) {
        if (d.watchStatus === "watched" || d.watchStatus === "watching") {
          watched.add(d.title);
        }
        if (d.rating && d.rating >= 7) {
          ratedHigh.add(d.title);
        }
        if (d.rating && d.rating >= 8) {
          likedActresses.add(a._id);
        }
      }
    }

    const topGenres = Object.entries(genreCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([g]) => g);

    // Generate recommendations
    const recMap: Record<string, Recommendation> = {};

    for (const a of actresses) {
      for (const d of a.dramas || []) {
        const key = d.title;
        if (!recMap[key]) {
          recMap[key] = {
            dramaTitle: d.title,
            year: d.year,
            poster: d.poster,
            actress: { id: a._id, name: a.name, role: d.role, tier: a.tier },
            reasons: [],
            score: 0,
          };
        }

        const rec = recMap[key];

        // Reason: from a highly-ranked actress
        if (a.tier && TIER_WEIGHT[a.tier] >= 4) {
          const tierLabel = a.tier === "splus" ? "S+" : a.tier.toUpperCase();
          const reason = `${a.name} is ${tierLabel}-tier`;
          if (!rec.reasons.includes(reason)) {
            rec.reasons.push(reason);
            rec.score += TIER_WEIGHT[a.tier] * 2;
          }
        }

        // Reason: genre matches your preference
        if (topGenres.includes(a.genre)) {
          const reason = `Matches your ${a.genre} preference`;
          if (!rec.reasons.includes(reason)) {
            rec.reasons.push(reason);
            rec.score += 2;
          }
        }

        // Reason: from an actress you rated highly
        if (likedActresses.has(a._id) && !a.tier) {
          const reason = `You rated ${a.name}'s other dramas highly`;
          if (!rec.reasons.includes(reason)) {
            rec.reasons.push(reason);
            rec.score += 3;
          }
        }

        // Bonus: newer dramas get a slight boost
        if (d.year >= 2020) rec.score += 1;
        if (d.year >= 2023) rec.score += 1;

        // Already watched = lower priority but still show
        if (watched.has(d.title)) rec.score -= 5;
      }
    }

    const recs = Object.values(recMap)
      .filter((r) => r.reasons.length > 0)
      .sort((a, b) => b.score - a.score);

    return {
      recommendations: recs,
      watchedTitles: watched,
      genreProfile: topGenres,
    };
  }, [actresses]);

  const filtered = useMemo(() => {
    if (filter === "unwatched") return recommendations.filter((r) => !watchedTitles.has(r.dramaTitle));
    if (filter === "top") return recommendations.filter((r) => r.score >= 8);
    return recommendations;
  }, [recommendations, filter, watchedTitles]);

  return (
    <div className="detail-page">
      <button className="detail-back" onClick={() => navigate(-1)}>&#x2190; Back</button>
      <h1 className="recs-title">Drama Recommendations</h1>
      <p className="recs-subtitle">
        Based on your tier rankings, ratings, and genre preferences
        {genreProfile.length > 0 && (
          <span className="recs-profile"> — you like {genreProfile.join(", ")}</span>
        )}
      </p>

      <div className="recs-filters">
        {(["all", "unwatched", "top"] as const).map((f) => (
          <button
            key={f}
            className={`sort-pill ${filter === f ? "active" : ""}`}
            onClick={() => setFilter(f)}
          >
            {f === "all" ? "All" : f === "unwatched" ? "Unwatched Only" : "Top Picks"}
          </button>
        ))}
        <span className="recs-count">{filtered.length} recommendations</span>
      </div>

      <div className="recs-grid">
        {filtered.map((rec) => {
          const isWatched = watchedTitles.has(rec.dramaTitle);
          return (
            <div
              key={rec.dramaTitle}
              className={`recs-card ${isWatched ? "watched" : ""}`}
              onClick={() => navigate(`/drama/${encodeURIComponent(rec.dramaTitle)}`)}
            >
              {rec.poster ? (
                <img
                  className="recs-poster"
                  src={rec.poster}
                  alt={rec.dramaTitle}
                  referrerPolicy="no-referrer"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                />
              ) : (
                <div className="recs-poster-placeholder">
                  <span>{rec.dramaTitle.charAt(0)}</span>
                </div>
              )}
              <div className="recs-info">
                <span className="recs-drama-title">{rec.dramaTitle}</span>
                <span className="recs-drama-year">{rec.year}</span>
                <span className="recs-drama-actress">
                  {rec.actress.name} as {rec.actress.role}
                </span>
                {isWatched && <span className="recs-watched-badge">Watched</span>}
                <div className="recs-reasons">
                  {rec.reasons.map((r, i) => (
                    <span key={i} className="recs-reason-pill">{r}</span>
                  ))}
                </div>
                <div className="recs-score-bar">
                  <div
                    className="recs-score-fill"
                    style={{ width: `${Math.min((rec.score / 15) * 100, 100)}%` }}
                  />
                </div>
              </div>
            </div>
          );
        })}
        {filtered.length === 0 && (
          <div className="recs-empty">
            No recommendations yet — rank some actresses or rate dramas to get started!
          </div>
        )}
      </div>
    </div>
  );
}
