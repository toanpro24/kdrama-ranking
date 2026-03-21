import type { Actress, Stats } from "./types";

const BASE = "http://localhost:8000/api";

export async function fetchActresses(genre?: string, search?: string): Promise<Actress[]> {
  const params = new URLSearchParams();
  if (genre && genre !== "All") params.set("genre", genre);
  if (search) params.set("search", search);
  const res = await fetch(`${BASE}/actresses?${params}`);
  return res.json();
}

export async function createActress(data: { name: string; known: string; genre: string; year: number }): Promise<Actress> {
  const res = await fetch(`${BASE}/actresses`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function updateTier(id: string, tier: string | null): Promise<void> {
  await fetch(`${BASE}/actresses/${id}/tier`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tier }),
  });
}

export async function deleteActress(id: string): Promise<void> {
  await fetch(`${BASE}/actresses/${id}`, { method: "DELETE" });
}

export async function fetchStats(): Promise<Stats> {
  const res = await fetch(`${BASE}/stats`);
  return res.json();
}

export async function resetData(): Promise<void> {
  await fetch(`${BASE}/reset`, { method: "POST" });
}
