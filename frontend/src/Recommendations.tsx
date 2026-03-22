import { useState, useMemo, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { TIER_WEIGHT } from "./constants";
import { useActresses } from "./ActressContext";
import { askAI } from "./api";
import type { ChatMessage } from "./types";
import "./index.css";

interface Recommendation {
  dramaTitle: string;
  year: number;
  poster: string | null;
  actress: { id: string; name: string; role: string; tier: string | null };
  reasons: string[];
  score: number;
}

const SUGGESTED_PROMPTS = [
  "What should I watch next based on my ratings?",
  "Recommend a romance drama I haven't seen",
  "Which dramas from my list are must-watch?",
  "Suggest something similar to my highest-rated dramas",
];

export default function Recommendations() {
  const navigate = useNavigate();
  const { actresses, loading, reload } = useActresses();
  const [filter, setFilter] = useState<"all" | "unwatched" | "top">("all");

  // Chat state
  const [chatOpen, setChatOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function sendMessage(text: string) {
    if (!text.trim() || streaming) return;
    const userMsg: ChatMessage = { role: "user", content: text.trim() };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput("");
    setStreaming(true);

    let assistantContent = "";
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    askAI(
      newMessages,
      (chunk) => {
        assistantContent += chunk;
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = { role: "assistant", content: assistantContent };
          return updated;
        });
      },
      () => setStreaming(false),
      (err) => {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = { role: "assistant", content: `Error: ${err}` };
          return updated;
        });
        setStreaming(false);
      },
    );
  }

  if (loading) return <div className="loading-page"><div className="loading-spinner" /><span className="loading-text">Building recommendations...</span></div>;
  if (!actresses.length) return <div className="error-page"><span className="error-icon">!</span><span className="error-message">Could not load actresses</span><button className="error-retry" onClick={reload}>Try again</button></div>;

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

      {/* AI Chat Widget */}
      <div className={`chat-widget ${chatOpen ? "open" : ""}`}>
        <button className="chat-toggle" onClick={() => setChatOpen(!chatOpen)}>
          {chatOpen ? "✕" : "AI"}
        </button>
        {chatOpen && (
          <div className="chat-panel">
            <div className="chat-header">
              <span className="chat-header-title">K-Drama AI Assistant</span>
              <span className="chat-header-sub">Powered by Claude</span>
            </div>
            <div className="chat-messages">
              {messages.length === 0 && (
                <div className="chat-welcome">
                  <p>Ask me anything about K-Dramas! I know your tier rankings, ratings, and watch history.</p>
                  <div className="chat-suggestions">
                    {SUGGESTED_PROMPTS.map((p) => (
                      <button key={p} className="chat-suggestion" onClick={() => sendMessage(p)}>
                        {p}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {messages.map((m, i) => (
                <div key={i} className={`chat-msg chat-msg-${m.role}`}>
                  <div className="chat-msg-bubble">{m.content}{streaming && i === messages.length - 1 && m.role === "assistant" && <span className="chat-cursor">|</span>}</div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>
            <form className="chat-input-row" onSubmit={(e) => { e.preventDefault(); sendMessage(input); }}>
              <input
                className="chat-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about K-Dramas..."
                disabled={streaming}
              />
              <button className="chat-send" type="submit" disabled={streaming || !input.trim()}>
                {streaming ? "..." : "Send"}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
