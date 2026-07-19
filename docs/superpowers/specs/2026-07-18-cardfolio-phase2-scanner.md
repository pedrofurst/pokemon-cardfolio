# Cardfolio Phase 2 — Opportunity Scanner (spec)

**Date:** 2026-07-18  **Status:** Approved (autonomous build per owner directive)

## Purpose
Turn the stored price history into actionable signals: what moved, what looks cheap, and what hit a target price. Adds a watchlist so the user can track cards they don't own yet.

## Scope (in)
- **Watchlist:** track cards you don't own, with an optional `target_price`.
- **Richer price capture:** store TCGplayer `low/mid/high/market/directLow` per snapshot (not just market).
- **Signals** (`/opportunities`):
  - **Movers:** latest vs previous snapshot market price changed ≥ threshold % (default 10%).
  - **Deals:** latest snapshot `direct_low` ≤ market × (1 − threshold) (default 15%) → cheapest listing well under market.
  - **Target hits:** watchlist card whose latest market ≤ its `target_price`.
- **Refresh** covers owned ∪ watched cards.
- Frontend: an Opportunities page and watchlist management.

## Scope (out)
- Cross-marketplace spread (Liga BR / eBay) — no API. Deferred.
- Background scheduling — refresh stays on-demand (a `/prices/refresh` button already exists; movers/deals compute from whatever history exists).
- Notifications/email.

## Key decisions
- USD only (unchanged).
- Signals are computed from stored snapshots (no extra network calls at read time).
- Thresholds are query params with sensible defaults; no per-user config table yet.
- Multi-user-ready: `WatchItem.owner_id` like everything else.

## Data
- New model `WatchItem(id, owner_id="me", card_id→card.id, target_price: float|None, created_at)`.
- `PriceSnapshot` gains nullable `low, mid, high, direct_low` (keep `market_price`).

## Success criteria
- Can add/remove watchlist cards; refresh prices them too.
- `/opportunities` returns movers, deals, and target hits computed from stored snapshots.
- Opportunities page renders the three groups; watchlist visible/manageable.
- All layers tested (movers/deals/target logic with fake data); provider mapping of the extra fields tested with respx.
