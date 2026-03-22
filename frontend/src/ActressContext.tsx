import { createContext, useContext, useState, useCallback, useEffect } from "react";
import type { Actress } from "./types";
import { fetchActresses } from "./api";
import { useAuth } from "./AuthContext";

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

  const reload = useCallback(async () => {
    setLoading(true);
    setError(false);
    const data = await fetchActresses();
    setActresses(data);
    setLoading(false);
  }, []);

  useEffect(() => {
    if (!authLoading) reload();
  }, [user, authLoading, reload]);

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
