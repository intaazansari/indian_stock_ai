import { create } from "zustand";
import { persist } from "zustand/middleware";

interface WatchlistState {
  symbolSet: Set<string>;
  addToWatchlist: (symbol: string) => void;
  removeFromWatchlist: (symbol: string) => void;
  isInWatchlist: (symbol: string) => boolean;
}

export const useWatchlistStore = create<WatchlistState>()(
  persist(
    (set, get) => ({
      symbolSet: new Set<string>(),

      addToWatchlist: (symbol) =>
        set((state) => ({ symbolSet: new Set([...state.symbolSet, symbol]) })),

      removeFromWatchlist: (symbol) =>
        set((state) => {
          const next = new Set(state.symbolSet);
          next.delete(symbol);
          return { symbolSet: next };
        }),

      isInWatchlist: (symbol) => get().symbolSet.has(symbol),
    }),
    {
      name: "watchlist-storage",
      partialize: (state) => ({ symbolSet: [...state.symbolSet] }),
      merge: (persisted: unknown, current) => ({
        ...current,
        symbolSet: new Set((persisted as { symbolSet?: string[] })?.symbolSet ?? []),
      }),
    }
  )
);
