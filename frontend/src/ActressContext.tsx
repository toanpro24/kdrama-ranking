import { createContext, useContext, useState, useCallback, useEffect } from "react";
import type { Actress } from "./types";
import { fetchActresses } from "./api";

interface ActressContextValue {
  actresses: Actress[];
  loading: boolean;
  error: boolean;
  setActresses: React.Dispatch<React.SetStateAction<Actress[]>>;
  reload: () => Promise<void>;
}

const ActressContext = createContext<ActressContextValue | null>(null);

export function ActressProvider({ children }: { children: React.ReactNode }) {
  const [actresses, setActresses] = useState<Actress[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(false);
    const data = await fetchActresses();
    if (data.length === 0 && actresses.length === 0) {
      // Could be a real empty DB or a failed fetch — fetchActresses returns [] on error
      // We check if this is the initial load with no prior data
    }
    setActresses(data);
    setLoading(false);
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

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
