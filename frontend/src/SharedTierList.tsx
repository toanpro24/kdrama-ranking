import { useState, useEffect, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { fetchSharedTierList, isFollowing, followUser, unfollowUser } from "./api";
import type { SharedTierListData, Actress } from "./types";
import { TIERS } from "./constants";
import { useAuth } from "./AuthContext";
import "./index.css";

export default function SharedTierList() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [data, setData] = useState<SharedTierListData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [following, setFollowing] = useState(false);

  useEffect(() => {
    if (!slug) return;
    fetchSharedTierList(slug).then((d) => {
      if (d) {
        setData(d);
        // Update meta tags for social sharing
        const name = d.displayName || "Someone";
        document.title = `${name}'s K-Drama Tier List`;
        const setMeta = (prop: string, content: string) => {
          let el = document.querySelector(`meta[property="${prop}"]`) || document.querySelector(`meta[name="${prop}"]`);
          if (!el) { el = document.createElement("meta"); el.setAttribute(prop.startsWith("og:") ? "property" : "name", prop); document.head.appendChild(el); }
          el.setAttribute("content", content);
        };
        setMeta("og:title", `${name}'s K-Drama Tier List`);
        setMeta("og:description", d.bio || `Check out ${name}'s Korean drama actress rankings!`);
        setMeta("twitter:title", `${name}'s K-Drama Tier List`);
        setMeta("twitter:description", d.bio || `Check out ${name}'s Korean drama actress rankings!`);
      } else {
        setError("This tier list doesn't exist or is private.");
      }
      setLoading(false);
    });
    return () => { document.title = "K-Drama Actress Ranking"; };
  }, [slug]);

  useEffect(() => {
    if (!slug || !user) { setFollowing(false); return; }
    isFollowing(slug).then(setFollowing);
  }, [slug, user]);

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

  const handleToggleFollow = async () => {
    if (!slug) return;
    if (following) {
      const ok = await unfollowUser(slug);
      if (ok) setFollowing(false);
    } else {
      const ok = await followUser(slug);
      if (ok) setFollowing(true);
    }
  };

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
        {user && (
          <button className={`follow-btn ${following ? "following" : ""}`} onClick={handleToggleFollow}>
            {following ? "Following" : "Follow"}
          </button>
        )}
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
