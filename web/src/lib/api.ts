import { CardResult, CollectionResponse } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function json<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`API ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  searchCards: (q: string) =>
    fetch(`${BASE}/cards/search?q=${encodeURIComponent(q)}`).then(json<CardResult[]>),
  addHolding: (payload: Record<string, unknown>) =>
    fetch(`${BASE}/holdings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(json<unknown>),
  listHoldings: () => fetch(`${BASE}/holdings`).then(json<CollectionResponse>),
  refreshPrices: () =>
    fetch(`${BASE}/prices/refresh`, { method: "POST" }).then(json<{ written: number }>),
};
