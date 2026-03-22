import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useActresses } from "./ActressContext";
import ActressSelect from "./ActressSelect";
import "./index.css";

interface TimelineDrama {
  title: string;
  year: number;
  poster: string | null;
  actresses: { id: string; name: string; role: string }[];
}

export default function Timeline() {
  const navigate = useNavigate();
  const { actresses, loading, reload } = useActresses();
  const [filterActress, setFilterActress] = useState<string>("");
  const [tab, setTab] = useState<"drama" | "show">("drama");

  const dramasByYear = useMemo(() => {
    if (!actresses.length) return {} as Record<number, TimelineDrama[]>;
    const map: Record<string, TimelineDrama> = {};
    const filtered = filterActress
      ? actresses.filter((a) => a._id === filterActress)
      : actresses;

    for (const a of filtered) {
      for (const d of a.dramas || []) {
        const cat = (d as { category?: string }).category || "drama";
        if (cat !== tab) continue;
        if (!map[d.title]) {
          map[d.title] = { title: d.title, year: d.year, poster: d.poster, actresses: [] };
        }
        map[d.title].actresses.push({ id: a._id, name: a.name, role: d.role });
      }
    }

    const dramas = Object.values(map);
    dramas.sort((a, b) => b.year - a.year || a.title.localeCompare(b.title));

    const grouped: Record<number, TimelineDrama[]> = {};
    for (const d of dramas) {
      if (!grouped[d.year]) grouped[d.year] = [];
      grouped[d.year].push(d);
    }
    return grouped;
  }, [actresses, filterActress, tab]);

  const years = Object.keys(dramasByYear).map(Number).sort((a, b) => b - a);

  if (loading) return <div className="loading-page"><div className="loading-spinner" /><span className="loading-text">Loading timeline...</span></div>;
  if (!actresses.length) return <div className="error-page"><span className="error-icon">!</span><span className="error-message">Could not load actresses</span><button className="error-retry" onClick={reload}>Try again</button></div>;

  return (
    <div className="detail-page">
      <button className="detail-back" onClick={() => navigate(-1)}>&#x2190; Back</button>
      <h1 className="timeline-title">Browse {tab === "drama" ? "K-Dramas" : "TV Shows"}</h1>

      <div className="timeline-filters">
        <div className="timeline-tabs">
          <button className={`sort-pill ${tab === "drama" ? "active" : ""}`} onClick={() => setTab("drama")}>K-Dramas</button>
          <button className={`sort-pill ${tab === "show" ? "active" : ""}`} onClick={() => setTab("show")}>TV Shows</button>
        </div>
        <ActressSelect
          actresses={actresses}
          value={filterActress}
          onChange={setFilterActress}
          placeholder="All actresses"
          maxWidth={300}
        />
      </div>

      <div className="timeline-container">
        <div className="timeline-line" />
        {years.map((year) => (
          <div key={year} className="timeline-year-group">
            <div className="timeline-year-marker">{year}</div>
            <h2 className="timeline-year-label">{year}</h2>
            <div className="timeline-dramas">
              {dramasByYear[year].map((drama) => (
                <div
                  key={drama.title}
                  className="timeline-drama-card"
                  onClick={() => navigate(`/drama/${encodeURIComponent(drama.title)}`)}
                >
                  {drama.poster ? (
                    <img
                      className="timeline-poster"
                      src={drama.poster}
                      alt={drama.title}
                      referrerPolicy="no-referrer"
                      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                    />
                  ) : (
                    <div className="timeline-poster-placeholder">
                      <span>{drama.title.charAt(0)}</span>
                    </div>
                  )}
                  <div className="timeline-drama-info">
                    <span className="timeline-drama-name">{drama.title}</span>
                    <span className="timeline-drama-actress">
                      {drama.actresses.map((a) => `${a.name} (${a.role})`).join(", ")}
                    </span>
                    <div className="timeline-drama-meta">
                      <span>{drama.actresses.length} actress{drama.actresses.length !== 1 ? "es" : ""}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
