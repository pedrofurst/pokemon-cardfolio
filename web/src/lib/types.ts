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
