import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { fetchProfile, updateProfile } from "./api";
import type { UserProfile } from "./types";
import { useAuth } from "./AuthContext";
import { toast } from "./toast";
import "./index.css";

const VISIBILITY_OPTIONS = [
  { value: "private", label: "Private", desc: "Only you can see your tier list" },
  { value: "link_only", label: "Link Only", desc: "Anyone with the link can view" },
  { value: "public", label: "Public", desc: "Visible on leaderboards and discoverable" },
] as const;

export default function UserSettings() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Form fields
  const [displayName, setDisplayName] = useState("");
  const [bio, setBio] = useState("");
  const [shareSlug, setShareSlug] = useState("");
  const [visibility, setVisibility] = useState<"private" | "link_only" | "public">("private");

  useEffect(() => {
    if (!user) { setLoading(false); return; }
    fetchProfile().then((p) => {
      if (p) {
        setProfile(p);
        setDisplayName(p.displayName);
        setBio(p.bio);
        setShareSlug(p.shareSlug);
        setVisibility(p.tierListVisibility);
      }
      setLoading(false);
    });
  }, [user]);

  const hasChanges = profile && (
    displayName !== profile.displayName ||
    bio !== profile.bio ||
    shareSlug !== profile.shareSlug ||
    visibility !== profile.tierListVisibility
  );

  const handleSave = useCallback(async () => {
    if (!hasChanges || saving) return;
    setSaving(true);
    try {
      const updated = await updateProfile({
        displayName,
        bio,
        shareSlug,
        tierListVisibility: visibility,
      });
      setProfile(updated);
      toast.success("Profile saved");
    } catch (e: any) {
      toast.error(e.message || "Failed to save profile");
    } finally {
      setSaving(false);
    }
  }, [displayName, bio, shareSlug, visibility, hasChanges, saving]);

  const shareUrl = `${window.location.origin}/tier-list/${shareSlug}`;

  const handleCopyLink = useCallback(() => {
    navigator.clipboard.writeText(shareUrl);
    toast.success("Link copied to clipboard");
  }, [shareUrl]);

  if (!user) {
    return (
      <div className="detail-page">
        <button className="detail-back" onClick={() => navigate("/")}>← Back to Tier List</button>
        <div className="settings-empty">
          <h2>Sign in to access settings</h2>
        </div>
      </div>
    );
  }

  if (loading) return <div className="loading">Loading profile...</div>;

  return (
    <div className="detail-page">
      <div className="detail-top-bar">
        <button className="detail-back" onClick={() => navigate("/")}>← Back to Tier List</button>
      </div>

      <div className="settings-container">
        <h1 className="settings-title">Profile Settings</h1>
        <p className="settings-subtitle">Manage your profile and sharing preferences</p>

        <div className="settings-section">
          <h2 className="settings-section-title">Profile</h2>
          <div className="settings-field">
            <label className="settings-label">Display Name</label>
            <input
              className="settings-input"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Your display name"
              maxLength={50}
            />
          </div>
          <div className="settings-field">
            <label className="settings-label">Bio</label>
            <textarea
              className="settings-input settings-textarea"
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              placeholder="Tell others about your K-Drama taste..."
              maxLength={200}
              rows={3}
            />
            <span className="settings-hint">{bio.length}/200</span>
          </div>
        </div>

        <div className="settings-section">
          <h2 className="settings-section-title">Sharing</h2>
          <div className="settings-field">
            <label className="settings-label">Share Link</label>
            <div className="settings-slug-row">
              <span className="settings-slug-prefix">{window.location.origin}/tier-list/</span>
              <input
                className="settings-input settings-slug-input"
                value={shareSlug}
                onChange={(e) => setShareSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-"))}
                placeholder="your-slug"
                maxLength={30}
              />
            </div>
            {visibility !== "private" && (
              <button className="settings-copy-btn" onClick={handleCopyLink}>Copy Share Link</button>
            )}
          </div>
          <div className="settings-field">
            <label className="settings-label">Tier List Visibility</label>
            <div className="settings-visibility-options">
              {VISIBILITY_OPTIONS.map((opt) => (
                <label key={opt.value} className={`settings-visibility-option ${visibility === opt.value ? "active" : ""}`}>
                  <input
                    type="radio"
                    name="visibility"
                    value={opt.value}
                    checked={visibility === opt.value}
                    onChange={() => setVisibility(opt.value)}
                  />
                  <div>
                    <span className="settings-visibility-label">{opt.label}</span>
                    <span className="settings-visibility-desc">{opt.desc}</span>
                  </div>
                </label>
              ))}
            </div>
          </div>
        </div>

        <div className="settings-actions">
          <button
            className="settings-save-btn"
            onClick={handleSave}
            disabled={!hasChanges || saving}
          >
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
}
