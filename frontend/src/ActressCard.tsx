import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import type { Actress } from "./types";
import { TIER_MAP } from "./constants";

interface Props {
  actress: Actress;
  color: string;
  canEdit: boolean;
  onRemove: (id: string) => void;
  onDragStart: (e: React.DragEvent, actress: Actress) => void;
  onTouchStart?: (e: React.TouchEvent, actressId: string) => void;
  onTouchMove?: (e: React.TouchEvent) => void;
  onTouchEnd?: () => void;
}

export default function ActressCard({ actress, color, canEdit, onRemove, onDragStart, onTouchStart, onTouchMove, onTouchEnd }: Props) {
  const [hovered, setHovered] = useState(false);
  const [popupPos, setPopupPos] = useState<"below" | "above">("below");
  const cardRef = useRef<HTMLDivElement>(null);
  const showTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const hideTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const navigate = useNavigate();
  const fallbackImg = `https://ui-avatars.com/api/?name=${encodeURIComponent(actress.name)}&size=200&background=1a1a2e&color=fff&bold=true`;
  const tier = actress.tier ? TIER_MAP[actress.tier] : null;

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
        role="button"
        tabIndex={0}
        aria-label={`${actress.name}, known for ${actress.known}, ${actress.genre}${tier ? `, ${tier.label} tier` : ", unranked"}`}
        draggable={canEdit}
        onDragStart={canEdit ? (e) => { clearTimeout(showTimer.current); clearTimeout(hideTimer.current); setHovered(false); onDragStart(e, actress); } : undefined}
        onTouchStart={canEdit && onTouchStart ? (e) => onTouchStart(e, actress._id) : undefined}
        onTouchMove={canEdit && onTouchMove ? onTouchMove : undefined}
        onTouchEnd={canEdit && onTouchEnd ? onTouchEnd : undefined}
        onClick={handleClick}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); navigate(`/actress/${actress._id}`); } }}
        style={{ borderLeftColor: color, cursor: canEdit ? "grab" : "pointer" }}
      >
        <img
          className="card-avatar"
          src={actress.image || fallbackImg}
          alt={actress.name}
          loading="lazy"
          referrerPolicy="no-referrer"
          onError={(e) => { (e.target as HTMLImageElement).src = fallbackImg; }}
        />
        <div className="card-body">
          <span className="card-name">{actress.name}</span>
          <span className="card-known">{actress.known}</span>
          <div className="card-meta-row">
            <span className="card-genre" style={{ borderColor: color + "44", color }}>{actress.genre}</span>
            {actress.birthDate && (
              <span className="card-age">{new Date().getFullYear() - parseInt(actress.birthDate.slice(0, 4))}</span>
            )}
            {actress.dramas?.length > 0 && (
              <span className="card-drama-count">{actress.dramas.filter((d) => d.category !== "show").length} dramas</span>
            )}
          </div>
        </div>
        {canEdit && <button className="remove-btn" onClick={() => onRemove(actress._id)} aria-label={`Remove ${actress.name}`} title="Remove">✕</button>}
      </div>

      {hovered && (
        <div className={`card-popup ${popupPos}`} onMouseEnter={() => clearTimeout(hideTimer.current)} onMouseLeave={handleMouseLeave}>
          <img
            className="popup-image"
            src={actress.image || fallbackImg}
            alt={actress.name}
            loading="lazy"
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
