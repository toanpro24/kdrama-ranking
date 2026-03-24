import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import type { Actress, WatchStatus } from "./types";
import { fetchActress, rateDrama, updateWatchStatus } from "./api";
import { TIER_MAP } from "./constants";
import { toast } from "./toast";
import { useAuth } from "./AuthContext";
import { useActresses } from "./ActressContext";
import "./index.css";

export default function ActressDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const { updateDrama } = useActresses();
  const [actress, setActress] = useState<Actress | null>(null);
  const [loading, setLoading] = useState(true);
  const [lightbox, setLightbox] = useState<string | null>(null);

  useEffect(() => {
    if (!id || authLoading) return;
    setLoading(true);
    fetchActress(id)
      .then((data) => { setActress(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [id, authLoading, user]);

  // Sync a drama field change to both local state and shared context
  const syncDrama = useCallback((dramaTitle: string, field: "rating" | "watchStatus", value: number | string | null) => {
    setActress((prev) => {
      if (!prev) return prev;
      return { ...prev, dramas: prev.dramas.map((d) => d.title === dramaTitle ? { ...d, [field]: value } : d) };
    });
    if (!id) return;
    updateDrama(id, dramaTitle, field, value);
  }, [id, updateDrama]);


  if (loading) return <div className="loading-page" role="status" aria-live="polite"><div className="loading-spinner" aria-hidden="true" /><span className="loading-text">Loading profile...</span></div>;
  if (!actress) return <div className="error-page"><span className="error-icon">!</span><span className="error-message">Actress not found</span><button className="error-retry" onClick={() => navigate(-1)}>Go back</button></div>;

  const tier = actress.tier ? TIER_MAP[actress.tier] : null;
  const fallbackImg = `https://ui-avatars.com/api/?name=${encodeURIComponent(actress.name)}&size=400&background=1a1a2e&color=fff&bold=true`;

  // Gallery photos only (no drama posters) — limit by tier
  const TIER_GALLERY_LIMIT: Record<string, number> = { splus: 10, s: 8, a: 5, b: 3, c: 2, d: 1 };
  const galleryPhotos = [...new Set(actress.gallery || [])];
  const galleryLimit = actress.tier ? (TIER_GALLERY_LIMIT[actress.tier] || 10) : galleryPhotos.length;
  const uniqueGallery = galleryPhotos.slice(0, galleryLimit);

  return (
    <div className="detail-page">
      {/* Lightbox */}
      {lightbox && (
        <div className="lightbox" onClick={() => setLightbox(null)}>
          <button className="lightbox-close" onClick={() => setLightbox(null)}>✕</button>
          <img src={lightbox} alt="Full size" className="lightbox-img" referrerPolicy="no-referrer" onClick={(e) => e.stopPropagation()} />
        </div>
      )}

      <div className="detail-top-bar">
        <button className="detail-back" onClick={() => navigate(-1)}>← Back to Tier List</button>
        <button
          className="detail-share-btn"
          onClick={() => {
            if (navigator.share) {
              navigator.share({ title: actress?.name || "Actress Profile", url: window.location.href });
            } else {
              navigator.clipboard.writeText(window.location.href);
              toast.success("Link copied!");
            }
          }}
        >
          Share
        </button>
      </div>

      {/* Hero Section */}
      <div className="detail-hero">
        <div className="detail-hero-bg" style={{ backgroundImage: `url(${actress.image || fallbackImg})` }} />
        <div className="detail-hero-overlay" />
        <div className="detail-hero-content">
          <img
            className="detail-portrait"
            src={actress.image || fallbackImg}
            alt={actress.name}
            referrerPolicy="no-referrer"
            onClick={() => setLightbox(actress.image || fallbackImg)}
            onError={(e) => { (e.target as HTMLImageElement).src = fallbackImg; }}
          />
          <div className="detail-hero-text">
            <h1 className="detail-name">{actress.name}</h1>
            {tier && (
              <div className="detail-tier-pill" style={{ background: tier.color + "22", borderColor: tier.color }}>
                <span className="detail-tier-letter" style={{ background: tier.color }}>{tier.label}</span>
                <span style={{ color: tier.color }}>{tier.desc} Tier</span>
              </div>
            )}
            {!tier && <div className="detail-tier-pill unranked"><span style={{ color: "#666" }}>Unranked</span></div>}
            <p className="detail-tagline">Best known for <strong>{actress.known}</strong> ({actress.year})</p>
          </div>
        </div>
      </div>

      {/* Info Grid */}
      <div className="detail-grid">
        {/* Personal Info Card */}
        <div className="detail-section">
          <h2 className="detail-section-title">Personal Information</h2>
          <div className="detail-info-grid">
            <div className="detail-info-item">
              <span className="detail-info-icon">&#x1F382;</span>
              <div>
                <span className="detail-info-label">Born</span>
                <span className="detail-info-value">{actress.birthDate || "Unknown"}</span>
              </div>
            </div>
            <div className="detail-info-item">
              <span className="detail-info-icon">&#x1F4CD;</span>
              <div>
                <span className="detail-info-label">Birthplace</span>
                <span className="detail-info-value">{actress.birthPlace || "Unknown"}</span>
              </div>
            </div>
            <div className="detail-info-item">
              <span className="detail-info-icon">&#x1F3AC;</span>
              <div>
                <span className="detail-info-label">Primary Genre</span>
                <span className="detail-info-value">{actress.genre}</span>
              </div>
            </div>
            <div className="detail-info-item">
              <span className="detail-info-icon">&#x1F3E2;</span>
              <div>
                <span className="detail-info-label">Agency</span>
                <span className="detail-info-value">{actress.agency || "Independent"}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Photo Gallery Card */}
        <div className="detail-section">
          <h2 className="detail-section-title">
            Photo Gallery
            <span className="detail-section-count">
              {uniqueGallery.length} photo{uniqueGallery.length !== 1 ? "s" : ""}
              {actress.tier && galleryPhotos.length > galleryLimit && ` of ${galleryPhotos.length}`}
            </span>
          </h2>
          <div className="detail-gallery">
            {uniqueGallery.map((img, i) => (
              <img
                key={i}
                className="detail-gallery-img"
                src={img}
                alt={`${actress.name} photo ${i + 1}`}
                loading="lazy"
                referrerPolicy="no-referrer"
                onClick={() => setLightbox(img)}
                onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
              />
            ))}
            {uniqueGallery.length === 0 && <p className="detail-empty">No gallery photos available.</p>}
          </div>
        </div>

        {/* Filmography - split into K-Dramas and TV Shows */}
        {(() => {
          const allDramas = actress.dramas || [];
          const kdramas = allDramas.filter((d) => d.category !== "show");
          const tvShows = allDramas.filter((d) => d.category === "show");

          const renderCard = (drama: typeof allDramas[0], i: number) => (
            <div key={i} className="detail-drama-card clickable">
              <div onClick={() => navigate(`/drama/${encodeURIComponent(drama.title)}`)}>
                {drama.poster ? (
                  <img
                    className="detail-drama-poster"
                    src={drama.poster}
                    alt={drama.title}
                    loading="lazy"
                    referrerPolicy="no-referrer"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                  />
                ) : (
                  <div className="detail-drama-poster-placeholder">
                    <span>{drama.title.charAt(0)}</span>
                  </div>
                )}
                <div className="detail-drama-card-info">
                  <span className="detail-drama-title">{drama.title}</span>
                  <span className="detail-drama-year-badge">{drama.year}</span>
                  {drama.role && <span className="detail-drama-role">as {drama.role}</span>}
                </div>
              </div>
              <div className="drama-rating" role="group" aria-label={`Rate ${drama.title}`} onClick={(e) => e.stopPropagation()}>
                {[...Array(10)].map((_, s) => (
                  <span
                    key={s}
                    role="button"
                    tabIndex={user ? 0 : -1}
                    aria-label={`${s + 1} star${s > 0 ? "s" : ""}`}
                    aria-pressed={(drama.rating || 0) > s}
                    className={`rating-star ${(drama.rating || 0) > s ? "filled" : ""} ${!user ? "disabled" : ""}`}
                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); (e.target as HTMLElement).click(); } }}
                    onClick={async () => {
                      if (!user) return;
                      const newRating = s + 1 === drama.rating ? null : s + 1;
                      const ok = await rateDrama(actress._id, drama.title, newRating);
                      if (ok) syncDrama(drama.title, "rating", newRating);
                    }}
                  >
                    ★
                  </span>
                ))}
                {drama.rating && <span className="rating-value">{drama.rating}/10</span>}
              </div>
              <div className="watch-status-row" role="group" aria-label={`Watch status for ${drama.title}`} onClick={(e) => e.stopPropagation()}>
                {(["watched", "watching", "plan_to_watch", "dropped"] as WatchStatus[]).map((ws) => (
                  <button
                    key={ws}
                    className={`watch-btn ${drama.watchStatus === ws ? "active" : ""} ws-${ws} ${!user ? "disabled" : ""}`}
                    aria-pressed={drama.watchStatus === ws}
                    disabled={!user}
                    onClick={async () => {
                      if (!user) return;
                      const newStatus = drama.watchStatus === ws ? null : ws;
                      const ok = await updateWatchStatus(actress._id, drama.title, newStatus);
                      if (ok) syncDrama(drama.title, "watchStatus", newStatus);
                    }}
                  >
                    {ws === "watched" ? "Watched" : ws === "watching" ? "Watching" : ws === "plan_to_watch" ? "Plan" : "Dropped"}
                  </button>
                ))}
              </div>
              <span className="drama-card-arrow" onClick={() => navigate(`/drama/${encodeURIComponent(drama.title)}`)}>&#x2192;</span>
            </div>
          );

          return (
            <>
              <div className="detail-section full-width">
                <h2 className="detail-section-title">
                  K-Dramas
                  <span className="detail-section-count">{kdramas.length} titles</span>
                </h2>
                <div className="detail-filmography-grid">
                  {kdramas.map((d, i) => renderCard(d, i))}
                </div>
                {kdramas.length === 0 && <p className="detail-empty">No K-Drama credits found.</p>}
              </div>
              {tvShows.length > 0 && (
                <div className="detail-section full-width">
                  <h2 className="detail-section-title">
                    TV Shows
                    <span className="detail-section-count">{tvShows.length} titles</span>
                  </h2>
                  <div className="detail-filmography-grid">
                    {tvShows.map((d, i) => renderCard(d, i))}
                  </div>
                </div>
              )}
            </>
          );
        })()}

        {/* Awards Card - full width */}
        <div className="detail-section full-width">
          <h2 className="detail-section-title">
            Awards & Recognition
            <span className="detail-section-count">{actress.awards?.length || 0} awards</span>
          </h2>
          <div className="detail-awards">
            {(actress.awards || []).map((award, i) => (
              <div key={i} className="detail-award-item">
                <span className="detail-award-icon">&#x1F3C6;</span>
                <span className="detail-award-text">{award}</span>
              </div>
            ))}
            {(!actress.awards || actress.awards.length === 0) && (
              <p className="detail-empty">No awards data available.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
