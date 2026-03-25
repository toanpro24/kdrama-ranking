import { useState, useEffect, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { fetchSharedTierList } from "./api";
import type { SharedTierListData, Actress } from "./types";
import { TIERS } from "./constants";
import "./index.css";

export default function SharedTierList() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<SharedTierListData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) return;
    fetchSharedTierList(slug).then((d) => {
      if (d) setData(d);
      else setError("This tier list doesn't exist or is private.");
      setLoading(false);
    });
  }, [slug]);

  const tierActresses = useMemo(() => {
    if (!data) return {};
    const map: Record<string, Actress[]> = {};
    TIERS.forEach((t) => (map[t.id] = []));
    data.actresses.forEach((a) => {
      if (a.tier && map[a.tier]) map[a.tier].push(a);
    });
    return map;
  }, [data]);

  const ranked = useMemo(() => data?.actresses.filter((a) => a.tier).length || 0, [data]);

  if (loading) return <div className="loading">Loading tier list...</div>;

  if (error || !data) {
    return (
      <div className="detail-page">
        <button className="detail-back" onClick={() => navigate("/")}>← Back to Home</button>
        <div className="settings-empty">
          <h2>{error || "Tier list not found"}</h2>
        </div>
      </div>
    );
  }

  return (
    <div className="detail-page">
      <button className="detail-back" onClick={() => navigate("/")}>← Back to Home</button>

      <div className="shared-header">
        {data.picture && <img className="shared-avatar" src={data.picture} alt="" referrerPolicy="no-referrer" />}
        <div>
          <h1 className="shared-name">{data.displayName || "Anonymous"}'s Tier List</h1>
          {data.bio && <p className="shared-bio">{data.bio}</p>}
          <p className="shared-stats">{ranked} ranked out of {data.actresses.length} actresses</p>
        </div>
      </div>

      <section className="tiers-section shared-tiers">
        {TIERS.map((tier) => (
          <div key={tier.id} className="tier-row">
            <div className="tier-label" style={{ background: tier.color }}>
              <span className="tier-label-text">{tier.label}</span>
              <span className="tier-count">{tierActresses[tier.id]?.length || 0}</span>
            </div>
            <div className="tier-content">
              {tierActresses[tier.id]?.map((a) => (
                <div key={a._id} className="shared-card" onClick={() => navigate(`/actress/${a._id}`)}>
                  {a.image ? (
                    <img className="shared-card-img" src={a.image} alt={a.name} />
                  ) : (
                    <div className="shared-card-placeholder">{a.name.charAt(0)}</div>
                  )}
                  <span className="shared-card-name">{a.name}</span>
                </div>
              ))}
              {(!tierActresses[tier.id] || tierActresses[tier.id].length === 0) && (
                <div className="empty-hint">No actresses in this tier</div>
              )}
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}
