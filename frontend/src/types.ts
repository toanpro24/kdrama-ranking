export type WatchStatus = "watched" | "watching" | "plan_to_watch" | "dropped" | null;

export interface Drama {
  title: string;
  year: number;
  role: string;
  poster: string | null;
  rating: number | null;
  watchStatus: WatchStatus;
  category: "drama" | "show";
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

export interface UserProfile {
  _id: string;
  userId: string;
  displayName: string;
  bio: string;
  shareSlug: string;
  tierListVisibility: "private" | "link_only" | "public";
  picture: string;
}

export interface SharedTierListData {
  displayName: string;
  bio: string;
  picture: string;
  actresses: Actress[];
}

export interface LeaderboardEntry {
  rank: number;
  actressId: string;
  name: string;
  image: string | null;
  known: string;
  genre: string;
  totalLists: number;
  avgScore: number;
  topTierCount: number;
  tierCounts: Record<string, number>;
}

export interface LeaderboardData {
  entries: LeaderboardEntry[];
  totalUsers: number;
}

export interface CommunityStats {
  totalLists: number;
  avgScore: number;
  tierCounts: Record<string, number>;
  topTierCount: number;
  rank: number | null;
}

export interface FollowingUser {
  userId: string;
  displayName: string;
  picture: string;
  shareSlug: string;
  bio: string;
  rankedCount: number;
}

export interface TrendingEntry {
  rank: number;
  actressId: string;
  name: string;
  image: string | null;
  known: string;
  genre: string;
  userCount: number;
  avgScore: number;
  topTierCount: number;
  trendScore: number;
}

export interface TrendingData {
  entries: TrendingEntry[];
  totalUsers: number;
}

export interface CompareUser {
  displayName: string;
  picture: string;
  shareSlug: string;
  actresses: Actress[];
}

export interface CompareData {
  users: [CompareUser, CompareUser];
  stats: {
    commonActresses: number;
    exactMatches: number;
    agreementPct: number;
  };
}
