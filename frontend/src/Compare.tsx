import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import type { Actress } from "./types";
import { fetchActresses } from "./api";
import "./index.css";

const TIER_INFO: Record<string, { label: string; color: string }> = {
  splus: { label: "S+", color: "#E500A4" },
  s: { label: "S", color: "#FF2942" },
  a: { label: "A", color: "#FF7B3A" },
  b: { label: "B", color: "#FFC53A" },
  c: { label: "C", color: "#3AD9A0" },
  d: { label: "D", color: "#3A8FFF" },
};

export default function Compare() {
  const navigate = useNavigate();
  const [actresses, setActresses] = useState<Actress[]>([]);
  const [leftId, setLeftId] = useState<string>("");
  const [rightId, setRightId] = useState<string>("");

  useEffect(() => {
    fetchActresses().then(setActresses);
  }, []);

  const left = actresses.find((a) => a._id === leftId) || null;
  const right = actresses.find((a) => a._id === rightId) || null;
  const fallback = (name: string) =>
    `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&size=400&background=1a1a2e&color=fff&bold=true`;

  const sharedDramas = left && right
    ? left.dramas.filter((d) => right.dramas.some((rd) => rd.title === d.title)).map((d) => d.title)
    : [];

  const renderSide = (actress: Actress | null) => {
    if (!actress) return <div className="compare-empty">Select an actress above</div>;
    const tier = actress.tier ? TIER_INFO[actress.tier] : null;
    return (
      <div className="compare-profile">
        <img
          className="compare-avatar"
          src={actress.image || fallback(actress.name)}
          alt={actress.name}
          referrerPolicy="no-referrer"
          onError={(e) => { (e.target as HTMLImageElement).src = fallback(actress.name); }}
          onClick={() => navigate(`/actress/${actress._id}`)}
        />
        <h2 className="compare-name">{actress.name}</h2>
        {tier ? (
          <span className="compare-tier" style={{ background: tier.color + "22", color: tier.color, borderColor: tier.color + "44" }}>
            {tier.label} Tier
          </span>
        ) : (
          <span className="compare-tier unranked">Unranked</span>
        )}
        <div className="compare-stats-grid">
          <div className="compare-stat">
            <span className="compare-stat-label">Known For</span>
            <span className="compare-stat-value">{actress.known}</span>
          </div>
          <div className="compare-stat">
            <span className="compare-stat-label">Genre</span>
            <span className="compare-stat-value">{actress.genre}</span>
          </div>
          <div className="compare-stat">
            <span className="compare-stat-label">Dramas</span>
            <span className="compare-stat-value">{actress.dramas?.length || 0}</span>
          </div>
          <div className="compare-stat">
            <span className="compare-stat-label">Awards</span>
            <span className="compare-stat-value">{actress.awards?.length || 0}</span>
          </div>
          <div className="compare-stat">
            <span className="compare-stat-label">Agency</span>
            <span className="compare-stat-value">{actress.agency || "—"}</span>
          </div>
          <div className="compare-stat">
            <span className="compare-stat-label">Born</span>
            <span className="compare-stat-value">{actress.birthDate || "—"}</span>
          </div>
        </div>
        <h3 className="compare-section-title">Filmography</h3>
        <div className="compare-drama-list">
          {(actress.dramas || []).map((d, i) => (
            <div key={i} className={`compare-drama-item ${sharedDramas.includes(d.title) ? "shared" : ""}`}>
              <span className="compare-drama-title">{d.title}</span>
              <span className="compare-drama-year">{d.year}</span>
              {d.rating && <span className="compare-drama-rating">★ {d.rating}</span>}
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="detail-page">
      <button className="detail-back" onClick={() => navigate(-1)}>&#x2190; Back</button>
      <h1 className="compare-title">Compare Actresses</h1>
      <div className="compare-selectors">
        <select className="compare-select" value={leftId} onChange={(e) => setLeftId(e.target.value)}>
          <option value="">Select actress...</option>
          {actresses.map((a) => (
            <option key={a._id} value={a._id} disabled={a._id === rightId}>{a.name}</option>
          ))}
        </select>
        <span className="compare-vs">VS</span>
        <select className="compare-select" value={rightId} onChange={(e) => setRightId(e.target.value)}>
          <option value="">Select actress...</option>
          {actresses.map((a) => (
            <option key={a._id} value={a._id} disabled={a._id === leftId}>{a.name}</option>
          ))}
        </select>
      </div>
      {sharedDramas.length > 0 && (
        <div className="compare-shared">
          <span className="compare-shared-label">Shared dramas:</span>
          {sharedDramas.map((t) => <span key={t} className="compare-shared-pill">{t}</span>)}
        </div>
      )}
      <div className="compare-grid">
        {renderSide(left)}
        {renderSide(right)}
      </div>
    </div>
  );
}
