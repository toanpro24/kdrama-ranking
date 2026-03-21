import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import "./index.css";

const BASE = "http://localhost:8000/api";

interface CastMember {
  actressId: string;
  actressName: string;
  actressImage: string | null;
  role: string;
}

interface DramaInfo {
  title: string;
  year: number;
  poster: string | null;
  cast: CastMember[];
  network: string | null;
  episodes: number | null;
  genre: string | null;
  synopsis: string | null;
}

export default function DramaDetail() {
  const { title } = useParams<{ title: string }>();
  const navigate = useNavigate();
  const [drama, setDrama] = useState<DramaInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [lightbox, setLightbox] = useState<string | null>(null);

  useEffect(() => {
    if (!title) return;
    fetch(`${BASE}/dramas/${encodeURIComponent(title)}`)
      .then((r) => r.json())
      .then((data) => { setDrama(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [title]);

  if (loading) return <div className="loading">Loading...</div>;
  if (!drama) return <div className="loading">Drama not found.</div>;

  const fallbackPoster = `https://ui-avatars.com/api/?name=${encodeURIComponent(drama.title)}&size=400&background=1a1a2e&color=fff&bold=true&length=2`;

  return (
    <div className="detail-page">
      {lightbox && (
        <div className="lightbox" onClick={() => setLightbox(null)}>
          <button className="lightbox-close" onClick={() => setLightbox(null)}>&#x2715;</button>
          <img src={lightbox} alt="Full size" className="lightbox-img" onClick={(e) => e.stopPropagation()} />
        </div>
      )}

      <button className="detail-back" onClick={() => navigate(-1)}>&#x2190; Back</button>

      {/* Hero Section */}
      <div className="detail-hero drama-hero">
        <div className="detail-hero-bg" style={{ backgroundImage: `url(${drama.poster || fallbackPoster})` }} />
        <div className="detail-hero-overlay" />
        <div className="detail-hero-content drama-hero-content">
          <img
            className="drama-detail-poster"
            src={drama.poster || fallbackPoster}
            alt={drama.title}
            onClick={() => drama.poster && setLightbox(drama.poster)}
            onError={(e) => { (e.target as HTMLImageElement).src = fallbackPoster; }}
          />
          <div className="detail-hero-text">
            <h1 className="detail-name">{drama.title}</h1>
            <div className="drama-meta-pills">
              <span className="drama-meta-pill year-pill">{drama.year}</span>
              {drama.network && <span className="drama-meta-pill network-pill">{drama.network}</span>}
              {drama.episodes && <span className="drama-meta-pill episodes-pill">{drama.episodes} Episodes</span>}
            </div>
            {drama.genre && <p className="drama-genre-line">{drama.genre}</p>}
            {drama.synopsis && <p className="drama-synopsis">{drama.synopsis}</p>}
          </div>
        </div>
      </div>

      {/* Content Grid */}
      <div className="detail-grid">
        {/* Drama Info Card */}
        <div className="detail-section">
          <h2 className="detail-section-title">Drama Details</h2>
          <div className="detail-info-grid">
            <div className="detail-info-item">
              <span className="detail-info-icon">&#x1F4C5;</span>
              <div>
                <span className="detail-info-label">Year</span>
                <span className="detail-info-value">{drama.year}</span>
              </div>
            </div>
            <div className="detail-info-item">
              <span className="detail-info-icon">&#x1F4FA;</span>
              <div>
                <span className="detail-info-label">Network</span>
                <span className="detail-info-value">{drama.network || "Unknown"}</span>
              </div>
            </div>
            <div className="detail-info-item">
              <span className="detail-info-icon">&#x1F3AC;</span>
              <div>
                <span className="detail-info-label">Episodes</span>
                <span className="detail-info-value">{drama.episodes || "Unknown"}</span>
              </div>
            </div>
            <div className="detail-info-item">
              <span className="detail-info-icon">&#x1F3AD;</span>
              <div>
                <span className="detail-info-label">Genre</span>
                <span className="detail-info-value">{drama.genre || "Unknown"}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Cast Card */}
        <div className="detail-section">
          <h2 className="detail-section-title">
            Cast from Our Database
            <span className="detail-section-count">{drama.cast.length} actress{drama.cast.length !== 1 ? "es" : ""}</span>
          </h2>
          <div className="drama-cast-grid">
            {drama.cast.map((member) => {
              const fallbackAvatar = `https://ui-avatars.com/api/?name=${encodeURIComponent(member.actressName)}&size=200&background=1a1a2e&color=fff&bold=true`;
              return (
                <div
                  key={member.actressId}
                  className="drama-cast-card"
                  onClick={() => navigate(`/actress/${member.actressId}`)}
                >
                  <img
                    className="drama-cast-avatar"
                    src={member.actressImage || fallbackAvatar}
                    alt={member.actressName}
                    onError={(e) => { (e.target as HTMLImageElement).src = fallbackAvatar; }}
                  />
                  <div className="drama-cast-info">
                    <span className="drama-cast-name">{member.actressName}</span>
                    {member.role && <span className="drama-cast-role">as {member.role}</span>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Synopsis Card - full width if available */}
        {drama.synopsis && (
          <div className="detail-section full-width">
            <h2 className="detail-section-title">Synopsis</h2>
            <p className="drama-synopsis-full">{drama.synopsis}</p>
          </div>
        )}
      </div>
    </div>
  );
}
