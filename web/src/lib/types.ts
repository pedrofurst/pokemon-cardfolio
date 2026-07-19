export interface CardResult {
  id: string;
  name: string;
  set_name: string;
  number: string;
  rarity: string;
  image_url: string;
  tcgplayer_id: string | null;
  market_price: number | null;
}

export interface HoldingView {
  holding: {
    id: string;
    card_id: string;
    condition: string;
    is_graded: boolean;
    acquisition_cost: number;
    quantity: number;
    notes: string;
  };
  card: { id: string; name: string; set_name: string; image_url: string } | null;
  current_price: number | null;
  pnl: number;
}

export interface CollectionResponse {
  summary: { total_cost: number; total_value: number; pnl: number; pnl_pct: number };
  items: HoldingView[];
}

export interface Signal {
  kind: string;
  card_id: string;
  card_name: string;
  detail: string;
  current_price: number | null;
  reference_price: number | null;
  change_pct: number | null;
}

export interface OpportunitiesResponse {
  movers: Signal[];
  deals: Signal[];
  target_hits: Signal[];
}

export interface WatchEntry {
  item: { id: string; card_id: string; target_price: number | null };
  card: { id: string; name: string; set_name: string; image_url: string } | null;
}

export interface GradingResult {
  raw_net: number;
  psa10_net: number | null;
  psa9_net: number | null;
  expected_graded_net: number | null;
  uplift: number | null;
  roi_pct: number | null;
  recommendation: string;
  rationale: string;
}

export interface PortfolioPoint {
  fetched_at: string;
  total_value: number;
  total_cost: number;
  pnl: number;
}

export interface PricePoint {
  fetched_at: string;
  market_price: number;
}

export interface PriceCheckResult {
  card_id: string;
  offer: number;
  market: number;
  low: number | null;
  direct_low: number | null;
  verdict: string;
  delta_pct: number;
  detail: string;
}

export interface PriceStatus {
  last_refresh: string | null;
}
