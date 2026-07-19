import {
  CardResult,
  CollectionResponse,
  GradingResult,
  OpportunitiesResponse,
  PortfolioPoint,
  PriceCheckResult,
  PricePoint,
  PriceStatus,
  WatchEntry,
} from "./types";

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
  listOpportunities: (moverPct?: number, dealPct?: number) => {
    const params = new URLSearchParams();
    if (moverPct !== undefined) {
      params.set("mover_pct", String(moverPct));
    }
    if (dealPct !== undefined) {
      params.set("deal_pct", String(dealPct));
    }
    const query = params.toString();
    return fetch(`${BASE}/opportunities${query ? `?${query}` : ""}`).then(
      json<OpportunitiesResponse>
    );
  },
  listWatchlist: () => fetch(`${BASE}/watchlist`).then(json<WatchEntry[]>),
  addWatch: (payload: Record<string, unknown>) =>
    fetch(`${BASE}/watchlist`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(json<unknown>),
  removeWatch: (id: string) =>
    fetch(`${BASE}/watchlist/${id}`, { method: "DELETE" }).then(json<{ deleted: boolean }>),
  evaluateGrading: (payload: Record<string, unknown>) =>
    fetch(`${BASE}/grading/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(json<GradingResult>),
  getPortfolioHistory: () =>
    fetch(`${BASE}/history/portfolio`).then(json<PortfolioPoint[]>),
  getCardHistory: (id: string) =>
    fetch(`${BASE}/history/card/${id}`).then(json<PricePoint[]>),
  checkPrice: (payload: Record<string, unknown>) =>
    fetch(`${BASE}/price-check`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(json<PriceCheckResult>),
  getPriceStatus: () => fetch(`${BASE}/prices/status`).then(json<PriceStatus>),
};
