import { useState, useEffect, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { fetchCompare } from "./api";
import type { CompareData, Actress } from "./types";
import { TIERS } from "./constants";
import "./index.css";

const TIER_COLORS: Record<string, string> = {};
TIERS.forEach((t) => { TIER_COLORS[t.id] = t.color; });

function TierPill({ tier }: { tier: string | null }) {
  if (!tier) return <span className="cl-tier-pill cl-unranked">—</span>;
  const t = TIERS.find((t) => t.id === tier);
  return (
    <span className="cl-tier-pill" style={{ background: t?.color || "#555" }}>
      {t?.label || tier}
    </span>
  );
}

export default function CompareLists() {
  const { slug1, slug2 } = useParams<{ slug1: string; slug2: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<CompareData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!slug1 || !slug2) return;
    fetchCompare(slug1, slug2).then((d) => {
      if (d) setData(d);
      else setError("Could not load comparison. One or both tier lists may be private or not found.");
      setLoading(false);
    });
  }, [slug1, slug2]);

  // Build combined actress list with both users' tiers
  const rows = useMemo(() => {
    if (!data) return [];
    const map = new Map<string, { actress: Actress; tier1: string | null; tier2: string | null }>();

    for (const a of data.users[0].actresses) {
      map.set(a._id, { actress: a, tier1: a.tier, tier2: null });
    }
    for (const a of data.users[1].actresses) {
      const existing = map.get(a._id);
      if (existing) {
        existing.tier2 = a.tier;
      } else {
        map.set(a._id, { actress: a, tier1: null, tier2: a.tier });
      }
    }

    // Sort: both ranked first (by tier1), then only one ranked, then unranked
    const tierOrder = ["splus", "s", "a", "b", "c", "d"];
    return [...map.values()]
      .filter((r) => r.tier1 || r.tier2)
      .sort((a, b) => {
        const ai = a.tier1 ? tierOrder.indexOf(a.tier1) : 99;
        const bi = b.tier1 ? tierOrder.indexOf(b.tier1) : 99;
        return ai - bi;
      });
  }, [data]);

  if (loading) return <div className="loading">Loading comparison...</div>;

  if (error || !data) {
    return (
      <div className="detail-page">
        <button className="detail-back" onClick={() => navigate("/")}>← Back to Home</button>
        <div className="settings-empty">
          <h2>{error || "Comparison not found"}</h2>
        </div>
      </div>
    );
  }

  const [u1, u2] = data.users;

  return (
    <div className="detail-page">
      <button className="detail-back" onClick={() => navigate("/")}>← Back to Home</button>

      <h1 className="cl-title">Compare Tier Lists</h1>

      {/* User headers */}
      <div className="cl-users">
        <div className="cl-user" onClick={() => navigate(`/tier-list/${u1.shareSlug}`)}>
          {u1.picture && <img className="cl-user-avatar" src={u1.picture} alt="" referrerPolicy="no-referrer" />}
          <span className="cl-user-name">{u1.displayName || "User 1"}</span>
        </div>
        <div className="cl-vs">VS</div>
        <div className="cl-user" onClick={() => navigate(`/tier-list/${u2.shareSlug}`)}>
          {u2.picture && <img className="cl-user-avatar" src={u2.picture} alt="" referrerPolicy="no-referrer" />}
          <span className="cl-user-name">{u2.displayName || "User 2"}</span>
        </div>
      </div>

      {/* Agreement stats */}
      <div className="cl-agreement">
        <div className="cl-agreement-stat">
          <span className="cl-agreement-num">{data.stats.agreementPct}%</span>
          <span className="cl-agreement-label">Agreement</span>
        </div>
        <div className="cl-agreement-stat">
          <span className="cl-agreement-num">{data.stats.exactMatches}</span>
          <span className="cl-agreement-label">Exact Matches</span>
        </div>
        <div className="cl-agreement-stat">
          <span className="cl-agreement-num">{data.stats.commonActresses}</span>
          <span className="cl-agreement-label">Common Actresses</span>
        </div>
      </div>

      {/* Comparison table */}
      <div className="cl-table">
        <div className="cl-table-header">
          <span className="cl-col-tier">{u1.displayName?.split(" ")[0] || "User 1"}</span>
          <span className="cl-col-name">Actress</span>
          <span className="cl-col-tier">{u2.displayName?.split(" ")[0] || "User 2"}</span>
        </div>
        {rows.map((row) => {
          const match = row.tier1 && row.tier2 && row.tier1 === row.tier2;
          return (
            <div
              key={row.actress._id}
              className={`cl-table-row ${match ? "cl-match" : ""}`}
              onClick={() => navigate(`/actress/${row.actress._id}`)}
            >
              <div className="cl-col-tier">
                <TierPill tier={row.tier1} />
              </div>
              <div className="cl-col-name cl-actress-cell">
                {row.actress.image ? (
                  <img className="cl-actress-img" src={row.actress.image} alt={row.actress.name} />
                ) : (
                  <div className="cl-actress-placeholder">{row.actress.name.charAt(0)}</div>
                )}
                <span className="cl-actress-name">{row.actress.name}</span>
              </div>
              <div className="cl-col-tier">
                <TierPill tier={row.tier2} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
