import { useState, useRef, useEffect } from "react";
import type { Actress } from "./types";

interface Props {
  actresses: Actress[];
  value: string;
  onChange: (id: string) => void;
  disabledId?: string;
  placeholder?: string;
  maxWidth?: number;
}

const TIER_COLORS: Record<string, string> = {
  splus: "#E500A4", s: "#FF2942", a: "#FF7B3A",
  b: "#FFC53A", c: "#3AD9A0", d: "#3A8FFF",
};

export default function ActressSelect({ actresses, value, onChange, disabledId, placeholder = "Select actress...", maxWidth }: Props) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const ref = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const selected = actresses.find((a) => a._id === value) || null;

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  useEffect(() => {
    if (open && inputRef.current) inputRef.current.focus();
    if (!open) setSearch("");
  }, [open]);

  const filtered = actresses.filter((a) => {
    if (a._id === disabledId) return false;
    if (!search) return true;
    return a.name.toLowerCase().includes(search.toLowerCase()) ||
           a.known.toLowerCase().includes(search.toLowerCase());
  });

  const fallback = (name: string) =>
    `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&size=80&background=1a1a2e&color=fff&bold=true`;

  return (
    <div className="actress-select" ref={ref} style={maxWidth ? { maxWidth } : undefined}>
      <button
        className={`actress-select-trigger ${open ? "open" : ""}`}
        onClick={() => setOpen(!open)}
        type="button"
      >
        {selected ? (
          <span className="actress-select-chosen">
            <img
              className="actress-select-avatar"
              src={selected.image || fallback(selected.name)}
              alt=""
              referrerPolicy="no-referrer"
              onError={(e) => { (e.target as HTMLImageElement).src = fallback(selected.name); }}
            />
            <span className="actress-select-chosen-name">{selected.name}</span>
            {selected.tier && (
              <span className="actress-select-tier" style={{ color: TIER_COLORS[selected.tier] }}>
                {selected.tier === "splus" ? "S+" : selected.tier.toUpperCase()}
              </span>
            )}
          </span>
        ) : (
          <span className="actress-select-placeholder">{placeholder}</span>
        )}
        <span className="actress-select-arrow">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="actress-select-dropdown">
          <div className="actress-select-search-wrap">
            <input
              ref={inputRef}
              className="actress-select-search"
              placeholder="Search by name or drama..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="actress-select-list">
            {/* Clear option */}
            {value && (
              <button
                className="actress-select-option clear-option"
                onClick={() => { onChange(""); setOpen(false); }}
              >
                Clear selection
              </button>
            )}
            {filtered.map((a) => (
              <button
                key={a._id}
                className={`actress-select-option ${a._id === value ? "selected" : ""}`}
                onClick={() => { onChange(a._id); setOpen(false); }}
              >
                <img
                  className="actress-select-avatar"
                  src={a.image || fallback(a.name)}
                  alt=""
                  referrerPolicy="no-referrer"
                  onError={(e) => { (e.target as HTMLImageElement).src = fallback(a.name); }}
                />
                <div className="actress-select-option-info">
                  <span className="actress-select-option-name">{a.name}</span>
                  <span className="actress-select-option-known">{a.known}</span>
                </div>
                {a.tier && (
                  <span className="actress-select-tier" style={{ color: TIER_COLORS[a.tier] }}>
                    {a.tier === "splus" ? "S+" : a.tier.toUpperCase()}
                  </span>
                )}
              </button>
            ))}
            {filtered.length === 0 && (
              <div className="actress-select-empty">No matches found</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
