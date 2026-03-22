export type WatchStatus = "watched" | "watching" | "plan_to_watch" | "dropped" | null;

export interface Drama {
  title: string;
  year: number;
  role: string;
  poster: string | null;
  rating: number | null;
  watchStatus: WatchStatus;
}

export interface Actress {
  _id: string;
  name: string;
  known: string;
  genre: string;
  year: number;
  tier: string | null;
  image: string | null;
  birthDate: string | null;
  birthPlace: string | null;
  agency: string | null;
  dramas: Drama[];
  awards: string[];
  gallery: string[];
}

export interface Tier {
  id: string;
  label: string;
  color: string;
}

export interface Stats {
  total: number;
  ranked: number;
  unranked: number;
  genreCounts: Record<string, number>;
  tierCounts: Record<string, number>;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}
