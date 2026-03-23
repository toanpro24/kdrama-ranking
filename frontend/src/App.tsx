import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { toPng } from "html-to-image";
import type { Actress } from "./types";
import { createActress, updateTier, deleteActress, resetData, searchActressOnline, getActressFromTMDB } from "./api";
import type { ActressSearchResult } from "./api";
import { TIERS, GENRES } from "./constants";
import { useActresses } from "./ActressContext";
import { useAuth } from "./AuthContext";
import { useTouchDrag } from "./useTouchDrag";
import ActressCard from "./ActressCard";
import "./index.css";

export default function App() {
  const navigate = useNavigate();
  const { user, signInWithGoogle, logout } = useAuth();
  const { actresses, loading, reload, addActress, removeActress, updateActressTier } = useActresses();
  const [search, setSearch] = useState("");
  const [genreFilter, setGenreFilter] = useState("All");
  const [showAdd, setShowAdd] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [newName, setNewName] = useState("");
  const [newKnown, setNewKnown] = useState("");
  const [newGenre, setNewGenre] = useState("Romance");
  const [heroVisible, setHeroVisible] = useState(false);
  const [tiersVisible, setTiersVisible] = useState(false);
  const [dragOverTier, setDragOverTier] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<"default" | "name" | "year" | "genre">("default");
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [searchResults, setSearchResults] = useState<ActressSearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [addingFromTMDB, setAddingFromTMDB] = useState(false);
  const searchTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const tiersRef = useRef<HTMLElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const scrollRAF = useRef<number | null>(null);

  useEffect(() => {
    setTimeout(() => setHeroVisible(true), 100);
    setTimeout(() => setTiersVisible(true), 500);
  }, []);

  // Auto-scroll when dragging near viewport edges
  useEffect(() => {
    const EDGE_SIZE = 80;
    const MAX_SPEED = 18;

    function handleDragOver(e: DragEvent) {
      const y = e.clientY;
      const h = window.innerHeight;

      if (y < EDGE_SIZE) {
        const speed = MAX_SPEED * (1 - y / EDGE_SIZE);
        startAutoScroll(-speed);
      } else if (y > h - EDGE_SIZE) {
        const speed = MAX_SPEED * (1 - (h - y) / EDGE_SIZE);
        startAutoScroll(speed);
      } else {
        stopAutoScroll();
      }
    }

    function startAutoScroll(speed: number) {
      stopAutoScroll();
      function tick() {
        window.scrollBy(0, speed);
        scrollRAF.current = requestAnimationFrame(tick);
      }
      scrollRAF.current = requestAnimationFrame(tick);
    }

    function stopAutoScroll() {
      if (scrollRAF.current !== null) {
        cancelAnimationFrame(scrollRAF.current);
        scrollRAF.current = null;
      }
    }

    function handleDragEnd() {
      stopAutoScroll();
    }

    document.addEventListener("dragover", handleDragOver);
    document.addEventListener("dragend", handleDragEnd);
    document.addEventListener("drop", handleDragEnd);
    return () => {
      stopAutoScroll();
      document.removeEventListener("dragover", handleDragOver);
      document.removeEventListener("dragend", handleDragEnd);
      document.removeEventListener("drop", handleDragEnd);
    };
  }, []);

  useEffect(() => {
    if (!showUserMenu) return;
    function handleClickOutside(e: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setShowUserMenu(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [showUserMenu]);


  const tierActresses = useMemo(() => {
    const map: Record<string, Actress[]> = {};
    TIERS.forEach((t) => (map[t.id] = []));
    actresses.forEach((a) => {
      if (a.tier && map[a.tier]) map[a.tier].push(a);
    });
    return map;
  }, [actresses]);

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
    if (!user) return;
    const actressId = e.dataTransfer.getData("actressId");
    const sourceTier = e.dataTransfer.getData("sourceTier");
    const effectiveSrc = sourceTier === "unranked" ? null : sourceTier;
    if (effectiveSrc === targetTier) return;

    updateActressTier(actressId, targetTier);
    await updateTier(actressId, targetTier);
  }, [user]);

  // Touch drag-and-drop for mobile
  const handleTouchDrop = useCallback(async (actressId: string, targetTier: string | null) => {
    if (!user) return;
    const actress = actresses.find((a) => a._id === actressId);
    if (!actress) return;
    const sourceTier = actress.tier || null;
    if (sourceTier === targetTier) return;
    updateActressTier(actressId, targetTier);
    await updateTier(actressId, targetTier);
  }, [user, actresses, updateActressTier]);

  const { handleTouchStart, handleTouchMove, handleTouchEnd } = useTouchDrag({
    onDrop: handleTouchDrop,
    onDragOverTier: setDragOverTier,
  });

  const handleNameChange = useCallback((val: string) => {
    setNewName(val);
    clearTimeout(searchTimer.current);
    if (val.trim().length < 2) { setSearchResults([]); return; }
    setSearchLoading(true);
    searchTimer.current = setTimeout(async () => {
      const results = await searchActressOnline(val.trim());
      setSearchResults(results);
      setSearchLoading(false);
    }, 400);
  }, []);

  const handleSelectTMDB = useCallback(async (result: ActressSearchResult) => {
    setAddingFromTMDB(true);
    setSearchResults([]);
    try {
      const data = await getActressFromTMDB(result.tmdbId);
      const created = await createActress({
        name: data.name,
        known: data.known || "—",
        genre: data.genre || "Romance",
        year: data.year || 2024,
        image: data.image || undefined,
        birthDate: data.birthDate || undefined,
        birthPlace: data.birthPlace || undefined,
        dramas: data.dramas || [],
        gallery: data.gallery || [],
      });
      if (created) {
        addActress(created as Actress);
        setNewName("");
        setNewKnown("");
        setShowAdd(false);
      }
    } finally {
      setAddingFromTMDB(false);
    }
  }, []);

  const handleAddActress = useCallback(async () => {
    if (!newName.trim()) return;
    const created = await createActress({ name: newName.trim(), known: newKnown.trim() || "—", genre: newGenre, year: 2024 });
    if (!created) return;
    const actress: Actress = created;
    addActress(actress);
    setNewName("");
    setNewKnown("");
    setShowAdd(false);
  }, [newName, newKnown, newGenre]);

  const handleRemove = useCallback(async (id: string) => {
    removeActress(id);
    await deleteActress(id);
  }, [removeActress]);

  const handleReset = useCallback(async () => {
    await resetData();
    await reload();
  }, [reload]);

  const handleShareTierList = useCallback(async () => {
    if (!tiersRef.current) return;
    const el = tiersRef.current;
    // Temporarily disable animations and boost subtle backgrounds for capture
    const style = document.createElement("style");
    style.textContent = `
      .tiers-section * { animation: none !important; }
      .tier-row { background: rgba(255,255,255,0.06) !important; border-color: rgba(255,255,255,0.1) !important; }
      .actress-card { background: rgba(255,255,255,0.1) !important; }
    `;
    document.head.appendChild(style);
    try {
      const dataUrl = await toPng(el, {
        backgroundColor: "#0a0a0f",
        pixelRatio: 2,
        cacheBust: true,
      });
      const link = document.createElement("a");
      link.download = "my-kdrama-tier-list.png";
      link.href = dataUrl;
      link.click();
    } catch (err) {
      console.error("Screenshot failed:", err);
    } finally {
      document.head.removeChild(style);
    }
  }, []);

  if (loading) return <div className="loading" role="status" aria-live="polite">Loading actresses...</div>;

  return (
    <div>
      <a href="#main-content" className="skip-link">Skip to main content</a>
      {/* Hero */}
      <header className="hero" style={{ opacity: heroVisible ? 1 : 0, transform: heroVisible ? "none" : "translateY(30px)" }}>
        <div className="hero-glow" />
        <div className="hero-badge">K-DRAMA · ACTRESS RANKINGS</div>
        <h1 className="hero-title">
          <span className="hero-title-k">K-Drama</span>
          <br />
          <span className="hero-title-sub">Actress Tier List</span>
        </h1>
        <p className="hero-desc">
          Rank your favorite Korean drama actresses.
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
      <nav className="nav" aria-label="Main navigation">
        <div className="nav-tabs" role="tablist">
          <button onClick={() => navigate("/")} className="nav-tab active" role="tab" aria-selected="true" aria-current="page">⚡ Tier List</button>
          <button onClick={() => navigate("/stats")} className="nav-tab" role="tab" aria-selected="false">📊 Stats</button>
          <button onClick={() => navigate("/compare")} className="nav-tab" role="tab" aria-selected="false">⚔ Compare</button>
          <button onClick={() => navigate("/timeline")} className="nav-tab" role="tab" aria-selected="false">🎬 Browse Dramas</button>
          <button onClick={() => navigate("/recommendations")} className="nav-tab" role="tab" aria-selected="false">💡 For You</button>
          <button onClick={() => navigate("/watchlist")} className="nav-tab" role="tab" aria-selected="false">📺 Watch List</button>
        </div>
        <div className="nav-actions">
          <button onClick={handleShareTierList} className="nav-btn share-btn">📷 Share Tier List</button>
          {user && <button onClick={() => setShowResetConfirm(true)} className="nav-btn">↺ Reset</button>}
          {user && <button onClick={() => setShowAdd(!showAdd)} className="nav-btn primary">{showAdd ? "✕ Close" : "+ Add Actress"}</button>}
          {user ? (
            <div className="user-menu-wrap" ref={userMenuRef}>
              <button className="nav-btn user-btn" onClick={() => setShowUserMenu(!showUserMenu)}>
                <img className="user-avatar" src={user.photoURL || ""} alt="" referrerPolicy="no-referrer" />
                <span className="user-name">{user.displayName?.split(" ")[0]}</span>
              </button>
              {showUserMenu && (
                <div className="user-menu">
                  <div className="user-menu-header">
                    <img className="user-menu-avatar" src={user.photoURL || ""} alt="" referrerPolicy="no-referrer" />
                    <div className="user-menu-info">
                      <span className="user-menu-name">{user.displayName}</span>
                      <span className="user-menu-email">{user.email}</span>
                    </div>
                  </div>
                  <div className="user-menu-divider" />
                  <button className="user-menu-item" onClick={() => { setShowUserMenu(false); logout(); }}>Sign out</button>
                </div>
              )}
            </div>
          ) : (
            <button className="nav-btn primary google-btn" onClick={signInWithGoogle}>Sign in</button>
          )}
        </div>
      </nav>

      {!user && (
        <div className="guest-banner">
          <span>Sign in with Google to save your personal tier rankings, ratings, and watch list</span>
          <button className="guest-banner-btn" onClick={signInWithGoogle}>Sign in with Google</button>
        </div>
      )}

      {/* Reset Confirmation */}
      {showResetConfirm && (
        <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="reset-modal-title" onClick={() => setShowResetConfirm(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3 className="modal-title" id="reset-modal-title">Reset All Rankings?</h3>
            <p className="modal-text">This will remove all your tier placements, ratings, and watch statuses. This action cannot be undone.</p>
            <div className="modal-actions">
              <button className="modal-btn cancel" onClick={() => setShowResetConfirm(false)}>Cancel</button>
              <button className="modal-btn danger" onClick={() => { setShowResetConfirm(false); handleReset(); }}>Yes, Reset Everything</button>
            </div>
          </div>
        </div>
      )}

      {/* Add Form */}
      {showAdd && (
        <div className="add-panel">
          <div className="add-panel-inner">
            <h3 className="add-title">Add a New Actress</h3>
            <div className="add-search-section">
              <div className="add-field" style={{ position: "relative" }}>
                <label className="add-label">Search actress name</label>
                <input
                  value={newName}
                  onChange={(e) => handleNameChange(e.target.value)}
                  placeholder="e.g. Park Eun-bin"
                  className="add-input"
                  autoFocus
                />
                {searchLoading && <span className="add-search-spinner" />}
                {searchResults.length > 0 && (
                  <div className="add-search-dropdown">
                    {searchResults.map((r) => (
                      <div key={r.tmdbId} className="add-search-option" onClick={() => handleSelectTMDB(r)}>
                        {r.image ? (
                          <img className="add-search-avatar" src={r.image} alt={r.name} referrerPolicy="no-referrer" />
                        ) : (
                          <div className="add-search-avatar-placeholder">{r.name.charAt(0)}</div>
                        )}
                        <div className="add-search-info">
                          <span className="add-search-name">{r.name}</span>
                          {r.knownFor && <span className="add-search-known">{r.knownFor}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              {addingFromTMDB && <p className="add-search-status">Fetching actress data...</p>}
            </div>
            <div className="add-divider"><span>or add manually</span></div>
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
              <button onClick={handleAddActress} className="add-submit">Add Manually</button>
            </div>
          </div>
        </div>
      )}

      {/* Tier List */}
      <main id="main-content" className="main-content" aria-label="Tier list and unranked pool" style={{ opacity: tiersVisible ? 1 : 0, transform: tiersVisible ? "none" : "translateY(20px)", transition: "all 0.6s ease" }}>
          <section className="tiers-section" ref={tiersRef} aria-label="Tier rankings">
            {TIERS.map((tier, i) => (
              <div
                key={tier.id}
                data-tier-id={tier.id}
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
                    <ActressCard key={a._id} actress={a} color={tier.color} canEdit={!!user} onRemove={handleRemove} onDragStart={handleDragStart} onTouchStart={handleTouchStart} onTouchMove={handleTouchMove} onTouchEnd={handleTouchEnd} />
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
            data-tier-id="unranked"
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
                  <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search actresses..." className="search-input" aria-label="Search actresses" />
                </div>
                <div className="genre-pills" role="group" aria-label="Filter by genre">
                  {GENRES.map((g) => (
                    <button key={g} onClick={() => setGenreFilter(g)} className={`genre-pill ${genreFilter === g ? "active" : ""}`} aria-pressed={genreFilter === g}>{g}</button>
                  ))}
                </div>
                <div className="sort-pills" role="group" aria-label="Sort options">
                  <span className="sort-label">Sort:</span>
                  {(["default", "name", "year", "genre"] as const).map((s) => (
                    <button key={s} onClick={() => setSortBy(s)} className={`sort-pill ${sortBy === s ? "active" : ""}`} aria-pressed={sortBy === s}>
                      {s === "default" ? "Default" : s === "name" ? "A→Z" : s === "year" ? "Year ↓" : "Genre"}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="unranked-grid">
              {filteredUnranked.map((a) => (
                <ActressCard key={a._id} actress={a} color="#555" canEdit={!!user} onRemove={handleRemove} onDragStart={handleDragStart} onTouchStart={handleTouchStart} onTouchMove={handleTouchMove} onTouchEnd={handleTouchEnd} />
              ))}
              {filteredUnranked.length === 0 && (
                <div className="empty-hint">{unranked.length === 0 ? "All ranked! Add more above." : "No matches found."}</div>
              )}
            </div>
          </section>
        </main>

      {/* Footer */}
      <footer className="footer-section">
        <div className="footer-deco" />
        <p className="footer-text">Drag cards between tiers · Click cards for full profiles · Use filters to find actresses</p>
        <p className="footer-copy">K-Drama Actress Tier List · Made with ♡</p>
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
