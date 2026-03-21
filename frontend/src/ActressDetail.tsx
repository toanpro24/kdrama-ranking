import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import type { Actress, WatchStatus } from "./types";
import { rateDrama, updateWatchStatus } from "./api";
import { TIER_MAP } from "./constants";
import "./index.css";

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export default function ActressDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [actress, setActress] = useState<Actress | null>(null);
  const [loading, setLoading] = useState(true);
  const [lightbox, setLightbox] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${BASE}/actresses/${id}`)
      .then((r) => r.json())
      .then((data) => { setActress(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="loading-page"><div className="loading-spinner" /><span className="loading-text">Loading profile...</span></div>;
  if (!actress) return <div className="error-page"><span className="error-icon">!</span><span className="error-message">Actress not found</span><button className="error-retry" onClick={() => navigate(-1)}>Go back</button></div>;

  const tier = actress.tier ? TIER_MAP[actress.tier] : null;
  const fallbackImg = `https://ui-avatars.com/api/?name=${encodeURIComponent(actress.name)}&size=400&background=1a1a2e&color=fff&bold=true`;

  // Collect all available images for the gallery: main + gallery + drama posters
  const allGalleryImages = [
    ...(actress.gallery || []),
    ...(actress.dramas || []).filter(d => d.poster).map(d => d.poster as string),
  ];
  // Deduplicate
  const uniqueGallery = [...new Set(allGalleryImages)];

  return (
    <div className="detail-page">
      {/* Lightbox */}
      {lightbox && (
        <div className="lightbox" onClick={() => setLightbox(null)}>
          <button className="lightbox-close" onClick={() => setLightbox(null)}>✕</button>
          <img src={lightbox} alt="Full size" className="lightbox-img" referrerPolicy="no-referrer" onClick={(e) => e.stopPropagation()} />
        </div>
      )}

      <button className="detail-back" onClick={() => navigate(-1)}>← Back to Tier List</button>

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
            <span className="detail-section-count">{uniqueGallery.length} photos</span>
          </h2>
          <div className="detail-gallery">
            {uniqueGallery.map((img, i) => (
              <img
                key={i}
                className="detail-gallery-img"
                src={img}
                alt={`${actress.name} photo ${i + 1}`}
                referrerPolicy="no-referrer"
                onClick={() => setLightbox(img)}
                onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
              />
            ))}
            {uniqueGallery.length === 0 && <p className="detail-empty">No gallery photos available.</p>}
          </div>
        </div>

        {/* Filmography Card - full width with posters */}
        <div className="detail-section full-width">
          <h2 className="detail-section-title">
            Filmography
            <span className="detail-section-count">{actress.dramas?.length || 0} dramas</span>
          </h2>
          <div className="detail-filmography-grid">
            {(actress.dramas || []).map((drama, i) => (
              <div key={i} className="detail-drama-card clickable">
                <div onClick={() => navigate(`/drama/${encodeURIComponent(drama.title)}`)}>
                  {drama.poster ? (
                    <img
                      className="detail-drama-poster"
                      src={drama.poster}
                      alt={drama.title}
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
                <div className="drama-rating" onClick={(e) => e.stopPropagation()}>
                  {[...Array(10)].map((_, s) => (
                    <span
                      key={s}
                      className={`rating-star ${(drama.rating || 0) > s ? "filled" : ""}`}
                      onClick={() => {
                        const newRating = s + 1 === drama.rating ? null : s + 1;
                        rateDrama(actress._id, drama.title, newRating);
                        setActress((prev) => {
                          if (!prev) return prev;
                          const updated = { ...prev, dramas: prev.dramas.map((d, di) => di === i ? { ...d, rating: newRating } : d) };
                          return updated;
                        });
                      }}
                    >
                      ★
                    </span>
                  ))}
                  {drama.rating && <span className="rating-value">{drama.rating}/10</span>}
                </div>
                <div className="watch-status-row" onClick={(e) => e.stopPropagation()}>
                  {(["watched", "watching", "plan_to_watch", "dropped"] as WatchStatus[]).map((ws) => (
                    <button
                      key={ws}
                      className={`watch-btn ${drama.watchStatus === ws ? "active" : ""} ws-${ws}`}
                      onClick={() => {
                        const newStatus = drama.watchStatus === ws ? null : ws;
                        updateWatchStatus(actress._id, drama.title, newStatus);
                        setActress((prev) => {
                          if (!prev) return prev;
                          return { ...prev, dramas: prev.dramas.map((d, di) => di === i ? { ...d, watchStatus: newStatus } : d) };
                        });
                      }}
                    >
                      {ws === "watched" ? "Watched" : ws === "watching" ? "Watching" : ws === "plan_to_watch" ? "Plan" : "Dropped"}
                    </button>
                  ))}
                </div>
                <span className="drama-card-arrow" onClick={() => navigate(`/drama/${encodeURIComponent(drama.title)}`)}>&#x2192;</span>
              </div>
            ))}
          </div>
          {(!actress.dramas || actress.dramas.length === 0) && (
            <p className="detail-empty">No filmography data available.</p>
          )}
        </div>

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
