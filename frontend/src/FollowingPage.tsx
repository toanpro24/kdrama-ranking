import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { fetchFollowing, fetchFollowerCount, unfollowUser, fetchProfile } from "./api";
import type { FollowingUser, UserProfile } from "./types";
import { useAuth } from "./AuthContext";
import "./index.css";

export default function FollowingPage() {
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const [following, setFollowing] = useState<FollowingUser[]>([]);
  const [counts, setCounts] = useState({ followers: 0, following: 0 });
  const [myProfile, setMyProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    if (!user) { setLoading(false); return; }
    Promise.all([fetchFollowing(), fetchFollowerCount(), fetchProfile()]).then(([f, c, p]) => {
      setFollowing(f);
      setCounts(c);
      setMyProfile(p);
      setLoading(false);
    });
  }, [user, authLoading]);

  const handleUnfollow = async (slug: string) => {
    const ok = await unfollowUser(slug);
    if (ok) {
      setFollowing((prev) => prev.filter((u) => u.shareSlug !== slug));
      setCounts((prev) => ({ ...prev, following: Math.max(0, prev.following - 1) }));
    }
  };

  if (loading) return <div className="loading">Loading...</div>;

  if (!user) {
    return (
      <div className="detail-page">
        <button className="detail-back" onClick={() => navigate("/")}>← Back to Home</button>
        <div className="settings-empty">
          <h2>Sign in to see your following list</h2>
        </div>
      </div>
    );
  }

  return (
    <div className="detail-page">
      <button className="detail-back" onClick={() => navigate("/")}>← Back to Home</button>

      <h1 className="fw-title">Following</h1>

      <div className="fw-counts">
        <div className="fw-count-item">
          <span className="fw-count-num">{counts.followers}</span>
          <span className="fw-count-label">Followers</span>
        </div>
        <div className="fw-count-item">
          <span className="fw-count-num">{counts.following}</span>
          <span className="fw-count-label">Following</span>
        </div>
      </div>

      {following.length === 0 ? (
        <div className="fw-empty">
          <p>You're not following anyone yet.</p>
          <p className="fw-empty-hint">
            Visit the <span className="fw-link" onClick={() => navigate("/leaderboard")}>Leaderboard</span> or browse shared tier lists to find people to follow.
          </p>
        </div>
      ) : (
        <div className="fw-list">
          {following.map((u) => (
            <div key={u.userId} className="fw-card">
              <div className="fw-card-main" onClick={() => navigate(`/tier-list/${u.shareSlug}`)}>
                {u.picture ? (
                  <img className="fw-avatar" src={u.picture} alt="" referrerPolicy="no-referrer" />
                ) : (
                  <div className="fw-avatar-placeholder">{(u.displayName || "?").charAt(0)}</div>
                )}
                <div className="fw-info">
                  <span className="fw-name">{u.displayName || "User"}</span>
                  {u.bio && <span className="fw-bio">{u.bio}</span>}
                  <span className="fw-meta">{u.rankedCount} ranked</span>
                </div>
              </div>
              <div className="fw-actions">
                {myProfile?.shareSlug && myProfile.tierListVisibility !== "private" && (
                  <button
                    className="fw-compare-btn"
                    onClick={(e) => { e.stopPropagation(); navigate(`/compare-lists/${myProfile.shareSlug}/${u.shareSlug}`); }}
                    title="Compare tier lists"
                  >
                    Compare
                  </button>
                )}
                <button
                  className="fw-unfollow-btn"
                  onClick={(e) => { e.stopPropagation(); handleUnfollow(u.shareSlug); }}
                >
                  Unfollow
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
