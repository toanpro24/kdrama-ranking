export interface TierDef {
  id: string;
  label: string;
  color: string;
  desc: string;
}

export const TIERS: TierDef[] = [
  { id: "splus", label: "S+", color: "#E500A4", desc: "Legendary" },
  { id: "s", label: "S", color: "#FF2942", desc: "Outstanding" },
  { id: "a", label: "A", color: "#FF7B3A", desc: "Excellent" },
  { id: "b", label: "B", color: "#FFC53A", desc: "Great" },
  { id: "c", label: "C", color: "#3AD9A0", desc: "Good" },
  { id: "d", label: "D", color: "#3A8FFF", desc: "Decent" },
];

/** Quick lookup: tier id → { label, color, desc } */
export const TIER_MAP: Record<string, TierDef> = Object.fromEntries(
  TIERS.map((t) => [t.id, t])
);

/** Tier id → color string shortcut */
export const TIER_COLOR: Record<string, string> = Object.fromEntries(
  TIERS.map((t) => [t.id, t.color])
);

/** Tier id → scoring weight for recommendations */
export const TIER_WEIGHT: Record<string, number> = {
  splus: 6, s: 5, a: 4, b: 3, c: 2, d: 1,
};

export const GENRES = ["All", "Romance", "Fantasy", "Thriller", "Comedy", "Action", "Horror", "Historical", "Drama"];
