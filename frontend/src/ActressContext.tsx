import { createContext, useContext, useState, useCallback, useEffect } from "react";
import type { Actress } from "./types";
import { fetchActresses } from "./api";
import { useAuth } from "./AuthContext";

interface ActressContextValue {
  actresses: Actress[];
  loading: boolean;
  error: boolean;
  setActresses: React.Dispatch<React.SetStateAction<Actress[]>>;
  reload: () => Promise<void>;
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

  // Reload when auth state changes (login/logout)
  useEffect(() => {
    if (!authLoading) reload();
  }, [user, authLoading, reload]);

  return (
    <ActressContext.Provider value={{ actresses, loading, error, setActresses, reload }}>
      {children}
    </ActressContext.Provider>
  );
}

export function useActresses() {
  const ctx = useContext(ActressContext);
  if (!ctx) throw new Error("useActresses must be used within ActressProvider");
  return ctx;
}
