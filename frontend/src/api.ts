import type { Actress, Stats, ChatMessage } from "./types";
import { toast } from "./toast";

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
const ADMIN_KEY = import.meta.env.VITE_ADMIN_API_KEY || "";

// Auth token getter — set by AuthContext on mount
let _getToken: () => Promise<string | null> = async () => null;
export function setTokenGetter(fn: () => Promise<string | null>) {
  _getToken = fn;
}

async function authHeaders(): Promise<Record<string, string>> {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  const token = await _getToken();
  if (token) h["Authorization"] = `Bearer ${token}`;
  if (ADMIN_KEY) h["X-API-Key"] = ADMIN_KEY;
  return h;
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const headers = await authHeaders();
  const merged: RequestInit = {
    ...options,
    headers: { ...headers, ...(options?.headers as Record<string, string> || {}) },
  };
  const res = await fetch(url, merged);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const msg = body.detail || `Request failed (${res.status})`;
    throw new Error(msg);
  }
  return res.json();
}

export async function fetchActresses(genre?: string, search?: string): Promise<Actress[]> {
  const params = new URLSearchParams();
  if (genre && genre !== "All") params.set("genre", genre);
  if (search) params.set("search", search);
  try {
    return await request<Actress[]>(`${BASE}/actresses?${params}`);
  } catch (e: any) {
    toast.error("Failed to load actresses");
    return [];
  }
}

export async function createActress(data: { name: string; known: string; genre: string; year: number }): Promise<Actress | null> {
  try {
    const result = await request<Actress>(`${BASE}/actresses`, {
      method: "POST",
      body: JSON.stringify(data),
    });
    toast.success(`Added ${data.name}`);
    return result;
  } catch (e: any) {
    toast.error(e.message || "Failed to add actress");
    return null;
  }
}

export async function updateTier(id: string, tier: string | null): Promise<boolean> {
  try {
    await request(`${BASE}/actresses/${id}/tier`, {
      method: "PATCH",
      body: JSON.stringify({ tier }),
    });
    return true;
  } catch (e: any) {
    toast.error("Failed to update tier");
    return false;
  }
}

export async function deleteActress(id: string): Promise<boolean> {
  try {
    await request(`${BASE}/actresses/${id}`, { method: "DELETE" });
    return true;
  } catch (e: any) {
    toast.error("Failed to delete actress");
    return false;
  }
}

export async function fetchStats(): Promise<Stats | null> {
  try {
    return await request<Stats>(`${BASE}/stats`);
  } catch (e: any) {
    toast.error("Failed to load stats");
    return null;
  }
}

export async function resetData(): Promise<boolean> {
  try {
    await request(`${BASE}/reset`, { method: "POST" });
    toast.success("Data reset to defaults");
    return true;
  } catch (e: any) {
    toast.error("Failed to reset data");
    return false;
  }
}

export async function updateWatchStatus(actressId: string, dramaTitle: string, watchStatus: string | null): Promise<boolean> {
  try {
    await request(`${BASE}/actresses/${actressId}/dramas/${encodeURIComponent(dramaTitle)}/watch-status`, {
      method: "PATCH",
      body: JSON.stringify({ watchStatus }),
    });
    return true;
  } catch (e: any) {
    toast.error("Failed to update watch status");
    return false;
  }
}

export async function rateDrama(actressId: string, dramaTitle: string, rating: number | null): Promise<boolean> {
  try {
    await request(`${BASE}/actresses/${actressId}/dramas/${encodeURIComponent(dramaTitle)}/rating`, {
      method: "PATCH",
      body: JSON.stringify({ rating }),
    });
    return true;
  } catch (e: any) {
    toast.error("Failed to update rating");
    return false;
  }
}

export async function fetchDrama(title: string) {
  return request<any>(`${BASE}/dramas/${encodeURIComponent(title)}`);
}

export interface WatchlistItem {
  title: string;
  year: number;
  poster: string | null;
  watchStatus: string;
  actressId: string;
  cast: { actressId: string; actressName: string; role: string }[];
}

export async function fetchWatchlist(): Promise<WatchlistItem[]> {
  try {
    return await request<WatchlistItem[]>(`${BASE}/watchlist`);
  } catch {
    return [];
  }
}

export async function askAI(
  messages: ChatMessage[],
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: string) => void,
): Promise<void> {
  try {
    const headers = await authHeaders();
    const res = await fetch(`${BASE}/chat`, {
      method: "POST",
      headers,
      body: JSON.stringify({ messages }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed (${res.status})`);
    }
    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const payload = line.slice(6);
        if (payload === "[DONE]") { onDone(); return; }
        try {
          const parsed = JSON.parse(payload);
          if (parsed.text) onChunk(parsed.text);
        } catch { /* skip malformed */ }
      }
    }
    onDone();
  } catch (e: any) {
    onError(e.message || "Failed to get AI response");
  }
}
