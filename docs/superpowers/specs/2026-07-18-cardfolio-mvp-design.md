# Cardfolio — MVP Design (Phase 1)

**Date:** 2026-07-18
**Status:** Approved (design), pending implementation plan
**Author:** Pedro Furst (with Claude)

## Purpose

A portfolio manager for Pokémon trading cards. The owner tracks the cards they hold,
sees each card's live market value, and knows their profit/loss (P&L) — the same shape
as a stock portfolio tracker, but the asset is a card.

This is **not** investment advice tooling; it reports market data and computes P&L on
what the user chose to buy.

## Scope

### In scope (Phase 1 — this spec)
- Search a card catalog by name (via external API) and add owned copies to a collection.
- Store each owned card with acquisition cost, condition, quantity.
- Fetch current market price (USD) and store price history snapshots.
- Show the collection with per-card and total P&L.

### Out of scope (later phases)
- **Phase 2:** opportunity scanner — price alerts, cross-source spreads.
- **Phase 3:** grading decision helper — raw vs graded historical price minus grading cost.
- **Future product:** multi-user auth, Postgres, CSV import, hosting, image/scan entry.

## Key decisions (from brainstorming)
- **Phasing:** collection first (this spec), then scanner, then grading.
- **Price market:** global, in **USD**, via a clean API (no scraping of BR/Liga prices).
- **Audience:** product for others *eventually*, but MVP proves value for the owner first.
  Data model is multi-user-ready (`owner_id`) but the MVP has a single fixed user, no login.
- **Card entry:** manual **search & add** (type name → pick from results → enter cost/condition).
- **Where:** a **new standalone project** (`cardfolio`), not inside the trading-bot repo.

## Stack
- **Backend:** Python + FastAPI. Routers per resource; service / provider / repository layers.
- **DB:** SQLite for the MVP (file, zero setup). Access via **SQLModel/SQLAlchemy** so the
  migration to Postgres (when multi-user) is cheap.
- **Frontend:** Next.js (App Router) with a `lib/api.ts` client.
- **External HTTP:** `httpx`.

## Architecture

```
Frontend (Next.js)
      │  HTTP/JSON
Backend (FastAPI)
  ├─ routers/       → HTTP: validate request, shape response, translate errors, log
  ├─ services/      → business logic (P&L, value calc); lets errors bubble
  ├─ providers/     → external price API client, behind a PriceProvider interface
  └─ repositories/  → DB access (SQLite now, Postgres later)
```

**Why these boundaries**
- `PriceProvider` is an interface — swap `pokemontcg.io` for PokeWallet without touching
  business logic.
- `repository` isolates the DB — SQLite→Postgres does not touch services.
- Each unit is independently testable.

## Data model

### `card` — catalog cache (public info from the API; one row per real card)
| field | example | purpose |
|---|---|---|
| `id` | `base1-4` | API card id (PK) |
| `name` | Charizard | search/display |
| `set_name` | Base Set | context |
| `number` | 4/102 | identification |
| `rarity` | Rare Holo | filter |
| `image_url` | … | thumbnail |
| `tcgplayer_id` | … | price linkage |

### `holding` — a card the user owns (the core of the app)
| field | example | purpose |
|---|---|---|
| `id` | uuid | PK |
| `owner_id` | `me` | multi-user future |
| `card_id` | `base1-4` | → `card` |
| `condition` | NM / raw / PSA 10 | affects value |
| `is_graded` | false | raw vs graded |
| `acquisition_cost` | 120.00 | for P&L |
| `acquisition_date` | 2026-07-18 | history |
| `quantity` | 1 | duplicates |
| `notes` | free text | notes |

### `price_snapshot` — price history (trend, not just current value)
| field | example | purpose |
|---|---|---|
| `id` | uuid | PK |
| `card_id` | `base1-4` | → `card` |
| `source` | tcgplayer | provenance |
| `market_price` | 350.00 | price |
| `currency` | USD | currency |
| `fetched_at` | timestamp | when |

**P&L derivation:** current collection value = Σ(latest `price_snapshot` per `card` ×
`quantity`); cost = Σ(`acquisition_cost`); P&L = value − cost. Storing snapshots (not just
current price) feeds Phase 2 trend charts and alerts for free.

## Features (Phase 1)

### Screens (Next.js)
1. **Collection (home):** list of `holdings` (thumbnail, condition, cost, current value,
   per-card P&L). Summary cards on top: total cost, total value, total P&L (USD and %).
2. **Search & add:** search field → external API → result grid with images → click opens a
   modal for cost/condition/quantity → saves a `holding`.
3. **Card detail:** catalog info + a small `price_snapshot` trend chart.

### Flows
- **Add card:** type "Charizard" → backend queries `PriceProvider` → results (cached into
  `card`) → user picks + enters cost/condition → save `holding` → fetch price → save
  `price_snapshot`.
- **Refresh prices:** `POST /prices/refresh` iterates the collection's `card` rows, fetches
  current price, writes snapshots. MVP: on-demand ("Refresh prices" button). Later: scheduled job.

## External price provider
- **Primary source:** `pokemontcg.io` (Scrydex) — catalog + embedded TCGplayer prices,
  free with an API key. One API covers both search and price for the MVP.
- **Interface** `PriceProvider` with `search_cards(query)` and `get_price(card_id)`.
  Concrete: `PokemonTcgIoProvider`. Swapping to PokeWallet later = a new class.
- **API key in `.env`**, never in code.

## Error handling
- **Provider (external boundary):** wrap all `httpx` calls in try/except → typed domain
  errors (`PriceProviderError`, `CardNotFoundError`) with context. Light retry + timeout.
- **Services:** let errors bubble (no try/catch around provider/repo).
- **Routers:** translate domain errors → HTTP status + log once.

## Testing
- Unit tests per layer with the **provider mocked** (never hit the real API in tests).
- Services tested with a fake repository.
- One integration test of the flow: add card → snapshot → P&L.

## Success criteria (Phase 1)
- User can search a card by name and add an owned copy with cost/condition.
- Collection view shows each holding's current value and total P&L in USD.
- Prices refresh on demand and history is retained as snapshots.
- All layers unit-tested; provider mocked; one end-to-end flow test passes.
