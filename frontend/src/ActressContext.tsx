import { createContext, useContext, useState, useCallback, useEffect } from "react";
import type { Actress } from "./types";
import { fetchActresses } from "./api";

interface ActressContextValue {
  actresses: Actress[];
  loading: boolean;
  setActresses: React.Dispatch<React.SetStateAction<Actress[]>>;
  reload: () => Promise<void>;
}

const ActressContext = createContext<ActressContextValue | null>(null);

export function ActressProvider({ children }: { children: React.ReactNode }) {
  const [actresses, setActresses] = useState<Actress[]>([]);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    const data = await fetchActresses();
    setActresses(data);
    setLoading(false);
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  return (
    <ActressContext.Provider value={{ actresses, loading, setActresses, reload }}>
      {children}
    </ActressContext.Provider>
  );
}

export function useActresses() {
  const ctx = useContext(ActressContext);
  if (!ctx) throw new Error("useActresses must be used within ActressProvider");
  return ctx;
}
