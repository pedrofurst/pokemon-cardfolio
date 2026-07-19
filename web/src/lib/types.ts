export interface FxResponse {
  usd_brl: number;
}

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

export interface Sale {
  id: string;
  card_id: string;
  quantity: number;
  sale_price: number;
  fee: number;
  cost_basis: number;
  sold_at: string;
}

export interface SaleEntry {
  sale: Sale;
  card: { id: string; name: string; set_name: string; image_url: string } | null;
}

export interface RealizedSummary {
  total_proceeds: number;
  total_cost: number;
  realized_pnl: number;
  sales_count: number;
}

export interface SalesResponse {
  summary: RealizedSummary;
  items: SaleEntry[];
}

export interface DigestHolding {
  card_id: string;
  card_name: string;
  pnl: number;
  current_price: number | null;
}

export interface Digest {
  summary: { total_cost: number; total_value: number; pnl: number; pnl_pct: number };
  realized: RealizedSummary;
  top_gainer: DigestHolding | null;
  top_loser: DigestHolding | null;
  movers: Signal[];
  deals: Signal[];
  target_hits: Signal[];
  last_refresh: string | null;
}
