import { createContext, useContext, useState, useCallback, useEffect, useRef } from "react";
import type { Actress } from "./types";
import { fetchActresses } from "./api";
import { useAuth } from "./AuthContext";

const STALE_TIME = 60_000; // 1 minute — serve stale data while revalidating

interface ActressContextValue {
  actresses: Actress[];
  loading: boolean;
  error: boolean;
  reload: () => Promise<void>;
  addActress: (actress: Actress) => void;
  removeActress: (id: string) => void;
  updateActressTier: (id: string, tier: string | null) => void;
  updateDrama: (actressId: string, dramaTitle: string, field: "rating" | "watchStatus", value: number | string | null) => void;
}

const ActressContext = createContext<ActressContextValue | null>(null);

export function ActressProvider({ children }: { children: React.ReactNode }) {
  const { user, loading: authLoading } = useAuth();
  const [actresses, setActresses] = useState<Actress[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const lastFetch = useRef(0);

  const reload = useCallback(async (force = false) => {
    const now = Date.now();
    const hasData = actresses.length > 0;

    // SWR: if data is fresh, skip fetch
    if (!force && hasData && now - lastFetch.current < STALE_TIME) return;

    // Only show loading spinner on first load (no stale data to show)
    if (!hasData) setLoading(true);
    setError(false);
    const data = await fetchActresses();
    setActresses(data);
    lastFetch.current = Date.now();
    setLoading(false);
  }, [actresses.length]);

  useEffect(() => {
    if (!authLoading) reload(true);
  }, [user, authLoading]); // eslint-disable-line react-hooks/exhaustive-deps

  const addActress = useCallback((actress: Actress) => {
    setActresses((prev) => [...prev, actress]);
  }, []);

  const removeActress = useCallback((id: string) => {
    setActresses((prev) => prev.filter((a) => a._id !== id));
  }, []);

  const updateActressTier = useCallback((id: string, tier: string | null) => {
    setActresses((prev) =>
      prev.map((a) => (a._id === id ? { ...a, tier } : a))
    );
  }, []);

  const updateDrama = useCallback((actressId: string, dramaTitle: string, field: "rating" | "watchStatus", value: number | string | null) => {
    setActresses((prev) =>
      prev.map((a) =>
        a._id === actressId
          ? { ...a, dramas: a.dramas.map((d) => d.title === dramaTitle ? { ...d, [field]: value } : d) }
          : a
      )
    );
  }, []);

  return (
    <ActressContext.Provider value={{ actresses, loading, error, reload, addActress, removeActress, updateActressTier, updateDrama }}>
      {children}
    </ActressContext.Provider>
  );
}

export function useActresses() {
  const ctx = useContext(ActressContext);
  if (!ctx) throw new Error("useActresses must be used within ActressProvider");
  return ctx;
}
