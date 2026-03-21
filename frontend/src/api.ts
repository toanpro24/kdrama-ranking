import type { Actress, Stats } from "./types";
import { toast } from "./toast";

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
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
      headers: { "Content-Type": "application/json" },
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
      headers: { "Content-Type": "application/json" },
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
      headers: { "Content-Type": "application/json" },
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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rating }),
    });
    return true;
  } catch (e: any) {
    toast.error("Failed to update rating");
    return false;
  }
}
