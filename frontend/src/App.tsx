import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import html2canvas from "html2canvas";
import type { Actress, Tier, Stats } from "./types";
import { fetchActresses, createActress, updateTier, deleteActress, fetchStats, resetData } from "./api";
import "./index.css";

const DEFAULT_TIERS: Tier[] = [
  { id: "splus", label: "S+", color: "#E500A4" },
  { id: "s", label: "S", color: "#FF2942" },
  { id: "a", label: "A", color: "#FF7B3A" },
  { id: "b", label: "B", color: "#FFC53A" },
  { id: "c", label: "C", color: "#3AD9A0" },
  { id: "d", label: "D", color: "#3A8FFF" },
];

const GENRES = ["All", "Romance", "Fantasy", "Thriller", "Comedy", "Action", "Horror", "Historical", "Drama"];

const TIER_COLORS: Record<string, { label: string; color: string }> = {
  splus: { label: "S+", color: "#E500A4" },
  s: { label: "S", color: "#FF2942" },
  a: { label: "A", color: "#FF7B3A" },
  b: { label: "B", color: "#FFC53A" },
  c: { label: "C", color: "#3AD9A0" },
  d: { label: "D", color: "#3A8FFF" },
};

function ActressCard({
  actress,
  color,
  onRemove,
  onDragStart,
}: {
  actress: Actress;
  color: string;
  onRemove: (id: string) => void;
  onDragStart: (e: React.DragEvent, actress: Actress) => void;
}) {
  const [hovered, setHovered] = useState(false);
  const [popupPos, setPopupPos] = useState<"below" | "above">("below");
  const cardRef = useRef<HTMLDivElement>(null);
  const showTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const hideTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const navigate = useNavigate();
  const fallbackImg = `https://ui-avatars.com/api/?name=${encodeURIComponent(actress.name)}&size=200&background=1a1a2e&color=fff&bold=true`;
  const tier = actress.tier ? TIER_COLORS[actress.tier] : null;

  const handleMouseEnter = () => {
    clearTimeout(hideTimer.current);
    clearTimeout(showTimer.current);
    showTimer.current = setTimeout(() => {
      if (cardRef.current) {
        const rect = cardRef.current.getBoundingClientRect();
        setPopupPos(rect.top > 320 ? "above" : "below");
      }
      setHovered(true);
    }, 400);
  };

  const handleMouseLeave = () => {
    clearTimeout(showTimer.current);
    hideTimer.current = setTimeout(() => {
      setHovered(false);
    }, 100);
  };

  const handleClick = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest(".remove-btn")) return;
    navigate(`/actress/${actress._id}`);
  };

  return (
    <div
      ref={cardRef}
      className="actress-card-wrap"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <div
        className="actress-card"
        draggable
        onDragStart={(e) => { clearTimeout(showTimer.current); clearTimeout(hideTimer.current); setHovered(false); onDragStart(e, actress); }}
        onClick={handleClick}
        style={{ borderLeftColor: color }}
      >
        <img
          className="card-avatar"
          src={actress.image || fallbackImg}
          alt={actress.name}
          referrerPolicy="no-referrer"
          onError={(e) => { (e.target as HTMLImageElement).src = fallbackImg; }}
        />
        <div className="card-body">
          <span className="card-name">{actress.name}</span>
          <span className="card-known">{actress.known}</span>
          <span className="card-genre" style={{ borderColor: color + "44", color }}>{actress.genre}</span>
        </div>
        <button className="remove-btn" onClick={() => onRemove(actress._id)} title="Remove">✕</button>
      </div>

      {hovered && (
        <div className={`card-popup ${popupPos}`} onMouseEnter={() => clearTimeout(hideTimer.current)} onMouseLeave={handleMouseLeave}>
          <img
            className="popup-image"
            src={actress.image || fallbackImg}
            alt={actress.name}
            referrerPolicy="no-referrer"
            onError={(e) => { (e.target as HTMLImageElement).src = fallbackImg; }}
          />
          <div className="popup-info">
            <h3 className="popup-name">{actress.name}</h3>
            <div className="popup-detail-row">
              <span className="popup-label">Known For</span>
              <span className="popup-value">{actress.known}</span>
            </div>
            <div className="popup-detail-row">
              <span className="popup-label">Genre</span>
              <span className="popup-value">{actress.genre}</span>
            </div>
            <div className="popup-detail-row">
              <span className="popup-label">Year</span>
              <span className="popup-value">{actress.year}</span>
            </div>
            {tier && (
              <div className="popup-detail-row">
                <span className="popup-label">Tier</span>
                <span className="popup-value" style={{ color: tier.color, fontWeight: 700 }}>{tier.label}</span>
              </div>
            )}
            <span className="popup-hint">Click to view full profile →</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [actresses, setActresses] = useState<Actress[]>([]);
  const [loading, setLoading] = useState(true);
  const [tiers] = useState<Tier[]>(DEFAULT_TIERS);
  const [search, setSearch] = useState("");
  const [genreFilter, setGenreFilter] = useState("All");
  const [showAdd, setShowAdd] = useState(false);
  const [newName, setNewName] = useState("");
  const [newKnown, setNewKnown] = useState("");
  const [newGenre, setNewGenre] = useState("Romance");
  const [activeTab, setActiveTab] = useState("tierlist");
  const [heroVisible, setHeroVisible] = useState(false);
  const [tiersVisible, setTiersVisible] = useState(false);
  const [dragOverTier, setDragOverTier] = useState<string | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [sortBy, setSortBy] = useState<"default" | "name" | "year" | "genre">("default");
  const tiersRef = useRef<HTMLElement>(null);

  const loadData = useCallback(async () => {
    const data = await fetchActresses();
    setActresses(data);
    setLoading(false);
  }, []);

  const loadStats = useCallback(async () => {
    const data = await fetchStats();
    setStats(data);
  }, []);

  useEffect(() => {
    loadData();
    setTimeout(() => setHeroVisible(true), 100);
    setTimeout(() => setTiersVisible(true), 500);
  }, [loadData]);

  useEffect(() => {
    if (activeTab === "stats") loadStats();
  }, [activeTab, loadStats]);

  const tierActresses = useMemo(() => {
    const map: Record<string, Actress[]> = {};
    tiers.forEach((t) => (map[t.id] = []));
    actresses.forEach((a) => {
      if (a.tier && map[a.tier]) map[a.tier].push(a);
    });
    return map;
  }, [actresses, tiers]);

  const unranked = useMemo(() => actresses.filter((a) => !a.tier), [actresses]);

  const filteredUnranked = useMemo(() => {
    const filtered = unranked.filter((a) => {
      const matchSearch = !search || a.name.toLowerCase().includes(search.toLowerCase()) || a.known.toLowerCase().includes(search.toLowerCase());
      const matchGenre = genreFilter === "All" || a.genre === genreFilter;
      return matchSearch && matchGenre;
    });
    if (sortBy === "name") filtered.sort((a, b) => a.name.localeCompare(b.name));
    else if (sortBy === "year") filtered.sort((a, b) => b.year - a.year);
    else if (sortBy === "genre") filtered.sort((a, b) => a.genre.localeCompare(b.genre));
    return filtered;
  }, [unranked, search, genreFilter, sortBy]);

  const computedStats = useMemo(() => {
    const ranked = actresses.filter((a) => a.tier).length;
    const total = actresses.length;
    const genreCounts: Record<string, number> = {};
    actresses.forEach((a) => (genreCounts[a.genre] = (genreCounts[a.genre] || 0) + 1));
    const topGenre = Object.entries(genreCounts).sort((a, b) => b[1] - a[1])[0];
    return { ranked, total, topGenre: topGenre ? topGenre[0] : "N/A" };
  }, [actresses]);

  const handleDragStart = useCallback((e: React.DragEvent, actress: Actress) => {
    e.dataTransfer.setData("actressId", actress._id);
    e.dataTransfer.setData("sourceTier", actress.tier || "unranked");
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent, targetTier: string | null) => {
    e.preventDefault();
    setDragOverTier(null);
    const actressId = e.dataTransfer.getData("actressId");
    const sourceTier = e.dataTransfer.getData("sourceTier");
    const effectiveSrc = sourceTier === "unranked" ? null : sourceTier;
    if (effectiveSrc === targetTier) return;

    setActresses((prev) =>
      prev.map((a) => (a._id === actressId ? { ...a, tier: targetTier } : a))
    );
    await updateTier(actressId, targetTier);
  }, []);

  const handleAddActress = useCallback(async () => {
    if (!newName.trim()) return;
    const created = await createActress({ name: newName.trim(), known: newKnown.trim() || "—", genre: newGenre, year: 2024 });
    setActresses((prev) => [...prev, created]);
    setNewName("");
    setNewKnown("");
    setShowAdd(false);
  }, [newName, newKnown, newGenre]);

  const handleRemove = useCallback(async (id: string) => {
    setActresses((prev) => prev.filter((a) => a._id !== id));
    await deleteActress(id);
  }, []);

  const handleReset = useCallback(async () => {
    await resetData();
    await loadData();
  }, [loadData]);

  const handleShareTierList = useCallback(async () => {
    if (!tiersRef.current) return;
    try {
      const canvas = await html2canvas(tiersRef.current, {
        backgroundColor: "#0a0a0f",
        scale: 2,
        useCORS: true,
      });
      canvas.toBlob((blob) => {
        if (!blob) return;
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.download = "my-kdrama-tier-list.png";
        link.href = url;
        link.click();
        URL.revokeObjectURL(url);
      });
    } catch (err) {
      console.error("Screenshot failed:", err);
    }
  }, []);

  if (loading) return <div className="loading">Loading actresses...</div>;

  return (
    <div>
      {/* Hero */}
      <header className="hero" style={{ opacity: heroVisible ? 1 : 0, transform: heroVisible ? "none" : "translateY(30px)" }}>
        <div className="hero-glow" />
        <div className="hero-badge">TOAN PHAM · PERSONAL RANKINGS</div>
        <h1 className="hero-title">
          <span className="hero-title-k">Toan's K-Drama</span>
          <br />
          <span className="hero-title-sub">Actress Tier List</span>
        </h1>
        <p className="hero-desc">
          My personal ranking of the most talented Korean drama actresses.
          <br />Drag, drop & rank — {computedStats.total} actresses and counting.
        </p>
        <div className="hero-social-links">
          <a href="https://instagram.com/toanpc_" target="_blank" rel="noopener noreferrer" className="social-link instagram" title="Instagram">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/></svg>
            @toanpc_
          </a>
          <a href="https://github.com/toanpro24" target="_blank" rel="noopener noreferrer" className="social-link github" title="GitHub">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/></svg>
            toanpro24
          </a>
        </div>
        <div className="stats-bar">
          {[
            { num: computedStats.total, label: "Actresses" },
            { num: computedStats.ranked, label: "Ranked" },
            { num: computedStats.total - computedStats.ranked, label: "Unranked" },
            { num: computedStats.topGenre, label: "Top Genre" },
          ].map((s, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center" }}>
              {i > 0 && <div className="stat-divider" />}
              <div className="stat-item">
                <span className="stat-num">{s.num}</span>
                <span className="stat-label">{s.label}</span>
              </div>
            </div>
          ))}
        </div>
      </header>

      {/* Nav */}
      <nav className="nav">
        <div className="nav-tabs">
          {[["tierlist", "⚡ Tier List"], ["stats", "📊 Stats"]].map(([key, label]) => (
            <button key={key} onClick={() => setActiveTab(key)} className={`nav-tab ${activeTab === key ? "active" : ""}`}>{label}</button>
          ))}
        </div>
        <div className="nav-actions">
          <button onClick={handleShareTierList} className="nav-btn share-btn">📷 Share Tier List</button>
          <button onClick={handleReset} className="nav-btn">↺ Reset</button>
          <button onClick={() => setShowAdd(!showAdd)} className="nav-btn primary">{showAdd ? "✕ Close" : "+ Add Actress"}</button>
        </div>
      </nav>

      {/* Add Form */}
      {showAdd && (
        <div className="add-panel">
          <div className="add-panel-inner">
            <h3 className="add-title">Add a New Actress</h3>
            <div className="add-grid">
              <div className="add-field">
                <label className="add-label">Name *</label>
                <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="e.g. Park Eun-bin" className="add-input" onKeyDown={(e) => e.key === "Enter" && handleAddActress()} />
              </div>
              <div className="add-field">
                <label className="add-label">Known For</label>
                <input value={newKnown} onChange={(e) => setNewKnown(e.target.value)} placeholder="e.g. Extraordinary Attorney Woo" className="add-input" onKeyDown={(e) => e.key === "Enter" && handleAddActress()} />
              </div>
              <div className="add-field">
                <label className="add-label">Genre</label>
                <select value={newGenre} onChange={(e) => setNewGenre(e.target.value)} className="add-input">
                  {GENRES.filter((g) => g !== "All").map((g) => <option key={g}>{g}</option>)}
                </select>
              </div>
              <button onClick={handleAddActress} className="add-submit">Add to Pool</button>
            </div>
          </div>
        </div>
      )}

      {/* Tier List Tab */}
      {activeTab === "tierlist" && (
        <main className="main-content" style={{ opacity: tiersVisible ? 1 : 0, transform: tiersVisible ? "none" : "translateY(20px)", transition: "all 0.6s ease" }}>
          <section className="tiers-section" ref={tiersRef}>
            {tiers.map((tier, i) => (
              <div
                key={tier.id}
                className={`tier-row ${dragOverTier === tier.id ? "drag-over" : ""}`}
                style={{ animationDelay: `${i * 0.07}s` }}
                onDragOver={(e) => { handleDragOver(e); setDragOverTier(tier.id); }}
                onDragLeave={() => setDragOverTier(null)}
                onDrop={(e) => handleDrop(e, tier.id)}
              >
                <div className="tier-label" style={{ background: tier.color }}>
                  <span className="tier-label-text">{tier.label}</span>
                  <span className="tier-count">{tierActresses[tier.id]?.length || 0}</span>
                </div>
                <div className="tier-content">
                  {tierActresses[tier.id]?.map((a) => (
                    <ActressCard key={a._id} actress={a} color={tier.color} onRemove={handleRemove} onDragStart={handleDragStart} />
                  ))}
                  {(!tierActresses[tier.id] || tierActresses[tier.id].length === 0) && (
                    <div className="empty-hint">Drag actresses here</div>
                  )}
                </div>
              </div>
            ))}
          </section>

          {/* Unranked Pool */}
          <section
            className={`unranked-section ${dragOverTier === "unranked" ? "drag-over" : ""}`}
            onDragOver={(e) => { handleDragOver(e); setDragOverTier("unranked"); }}
            onDragLeave={() => setDragOverTier(null)}
            onDrop={(e) => handleDrop(e, null)}
          >
            <div className="unranked-head">
              <div>
                <h2 className="unranked-title">Unranked Pool</h2>
                <p className="unranked-sub">{filteredUnranked.length} of {unranked.length} showing</p>
              </div>
              <div className="filter-bar">
                <div className="search-wrap">
                  <span className="search-icon">⌕</span>
                  <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search actresses..." className="search-input" />
                </div>
                <div className="genre-pills">
                  {GENRES.map((g) => (
                    <button key={g} onClick={() => setGenreFilter(g)} className={`genre-pill ${genreFilter === g ? "active" : ""}`}>{g}</button>
                  ))}
                </div>
                <div className="sort-pills">
                  <span className="sort-label">Sort:</span>
                  {(["default", "name", "year", "genre"] as const).map((s) => (
                    <button key={s} onClick={() => setSortBy(s)} className={`sort-pill ${sortBy === s ? "active" : ""}`}>
                      {s === "default" ? "Default" : s === "name" ? "A→Z" : s === "year" ? "Year ↓" : "Genre"}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="unranked-grid">
              {filteredUnranked.map((a) => (
                <ActressCard key={a._id} actress={a} color="#555" onRemove={handleRemove} onDragStart={handleDragStart} />
              ))}
              {filteredUnranked.length === 0 && (
                <div className="empty-hint">{unranked.length === 0 ? "All ranked! Add more above." : "No matches found."}</div>
              )}
            </div>
          </section>
        </main>
      )}

      {/* Stats Tab */}
      {activeTab === "stats" && stats && (
        <main className="main-content">
          <section className="stats-page">
            <h2 className="stats-page-title">Your Ranking Breakdown</h2>
            <div className="stats-grid">
              <div className="stats-card">
                <h3 className="stats-card-title">Tier Distribution</h3>
                {tiers.map((t) => {
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
                {tiers.map((t) => {
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
      )}

      {/* Footer */}
      <footer className="footer-section">
        <div className="footer-deco" />
        <p className="footer-text">Drag cards between tiers · Click cards for full profiles · Use filters to find actresses</p>
        <p className="footer-copy">Toan Pham's K-Drama Actress Tier List · Made with ♡</p>
        <div className="footer-socials">
          <a href="https://instagram.com/toanpc_" target="_blank" rel="noopener noreferrer" title="Instagram">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/></svg>
          </a>
          <a href="https://github.com/toanpro24" target="_blank" rel="noopener noreferrer" title="GitHub">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/></svg>
          </a>
        </div>
      </footer>
    </div>
  );
}
