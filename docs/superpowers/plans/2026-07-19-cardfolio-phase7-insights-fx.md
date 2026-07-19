# Cardfolio Phase 7 (Insights, BRL, Variants, Reveal) Plan

**Goal:** (1) Set-completion progress + portfolio allocation ("Insights" page). (2) Global USD/BRL currency toggle (cached FX). (3) Condition & variant on add. (4) A CSS-3D "pack opening" reveal on add.

**Tech stack:** Python/FastAPI/SQLModel/httpx/pytest; Next 16/TS. No new frontend deps (reveal is CSS-3D).

## Global constraints
- Python 3.11+; TS. `owner_id` on new rows. External HTTP only in providers/ (FX included). Services bubble errors; routers translate via existing handlers.
- Tests never hit real network (mock FX + provider); scheduler off in tests. Don't regress 115 backend tests.
- Motion reduced-motion safe.

---

### BT1: Set data capture + Insights (progress + allocation)

**Files:** `backend/app/providers/base.py` (+set_id/set_total on CardResult), `backend/app/providers/pokemontcgio.py` (capture set.id + set.total), `backend/app/models.py` (Card +set_id, +set_total, +rarity already exists), `backend/app/services/collection_service.py` (persist set_id/set_total on upsert), new `backend/app/services/insights_service.py`, new `backend/app/routers/insights.py`, deps, main; tests.

- `CardResult` gains `set_id: str = ""`, `set_total: int | None = None`. Provider `_to_card_result`: `set_id = card["set"]["id"]`, `set_total = card["set"].get("total") or card["set"].get("printedTotal")`.
- `Card` model: add `set_id: str = ""`, `set_total: int | None = None`. `collection_service.add_holding_from_result` (and watch add in opportunity_service.add_watch) must pass set_id/set_total when upserting the Card.
- `InsightsService(card_repo, holding_repo, price_repo)`:
  - `set_progress(owner_id="me") -> list[dict]`: group owned holdings by the card's set_id; for each set with a known set_total, `{set_id, set_name, owned: <distinct card_ids owned in set>, total: set_total, pct}`. Skip sets with no set_total (or total None → still list owned with total null). Sort by pct desc.
  - `allocation(owner_id="me") -> dict`: using list_collection-style values (current_price*quantity), group value `by_set` (list of {name, value, pct}), `by_rarity` (list of {rarity, value, pct}), and `top_cards` (top 5 {card_id, name, value}). pct of total_value.
  - `build(owner_id) -> {"sets": set_progress(), "allocation": allocation()}`.
- Router `insights.py`: `GET /insights` → `service.build()`. Register + deps `get_insights_service`.
- Tests: seed cards with set_id/set_total + holdings → set_progress owned/total/pct; allocation by_set/by_rarity sums to total; top_cards ordering. Run pytest. Commit "feat(phase7): set progress + allocation insights".

---

### BT2: FX (USD→BRL) + Holding variant

**Files:** new `backend/app/providers/fx_provider.py`, new `backend/app/routers/fx.py`, `backend/app/models.py` (Holding +variant), `backend/app/routers/holdings.py` (+variant in AddHoldingRequest), `backend/app/services/collection_service.py` (pass variant), deps, main; tests.

- `fx_provider.py`: `FxProvider(client=None)` with `get_usd_brl() -> float` — GET `https://open.er-api.com/v6/latest/USD`, return `rates["BRL"]`. Wrap httpx in try/except → `PriceProviderError` (reuse) on failure. (External HTTP lives here, per layering.)
- Router `fx.py`: `GET /fx` → `{"usd_brl": <float>}`. Cache in-process for ~1h (module-level timestamp+value; since Date is available in Python runtime that's fine) to avoid hammering. On provider failure → let it bubble (502) OR return a sane fallback? Prefer: bubble to 502 (frontend falls back to USD). Add `get_fx_provider` to deps (singleton client).
- `Holding` model: add `variant: str = "normal"`. `AddHoldingRequest` (holdings router): add `variant: str = "normal"`. `collection_service.add_holding_from_result`: add a `variant` param (default "normal") and set it on the Holding; update the router call + any other callers/tests.
- Tests: FX provider maps rates["BRL"] (respx-mock the er-api); GET /fx returns usd_brl (override provider); adding a holding with variant persists it. Run pytest. Commit "feat(phase7): USD->BRL FX endpoint + holding variant".

---

### FT1: Currency context + toggle

**Files:** new `web/src/components/Currency.tsx` (CurrencyProvider + useMoney), `web/src/lib/api.ts` (+getFx), `web/src/lib/types.ts`, `web/src/app/layout.tsx` (wrap provider), `web/src/components/AppShell.tsx` (a USD/BRL toggle in the sidebar footer area).

- `Currency.tsx` ("use client"): `CurrencyProvider` holds `{currency: 'USD'|'BRL', rate: number|null, setCurrency}`. On mount, fetch `api.getFx()` once to get `usd_brl` (store rate); default currency USD; persist choice in `localStorage` (guard for SSR — read in effect, not render). `useMoney()` returns `fmt(valueUsd: number|null) => string` that converts to BRL when selected (value*rate) and formats with the right currency symbol (Intl.NumberFormat BRL/USD). If rate is null and BRL selected, fall back to USD formatting. Also export `useCurrency()` for the toggle.
- `api.ts`: `getFx(): Promise<{usd_brl:number}>`.
- layout: wrap app in `<CurrencyProvider>` (inside ToastProvider or around it).
- AppShell: a small segmented toggle (USD | BRL) in the sidebar footer; calls setCurrency.
- Verify tsc/lint/build. Commit "feat(phase7): currency context + USD/BRL toggle".

NOTE: This task ONLY adds the context/toggle + a `useMoney`. It does NOT yet convert every page (FT2 does the wiring where it matters most, to keep this task focused). Ensure it builds unused-but-exported.

---

### FT2: Apply currency + Insights page + variant UI + reveal

Split into sub-parts but one branch; do as separate commits if easier.

**2a — Apply currency to key money displays:** In `web/src/app/page.tsx` (collection hero + tiles), `today/page.tsx`, `sales/page.tsx`, `card/[id]/page.tsx`, replace the money value displays with `useMoney().fmt(...)` so the toggle affects them. (Prices from backend are USD; fmt converts.) Keep `pct` as-is. Don't break existing layout.

**2b — Insights page:** `web/src/lib/api.ts` (+getInsights), types; new `web/src/app/insights/page.tsx` — two sections: "Set completion" (progress bars per set: name, owned/total, % bar) and "Where your money is" (allocation: horizontal proportion bars by set and by rarity + a top-cards list). Use design-system classes; fmt for money. ConnectionError + load pattern. Nav: add "Insights" item (icon: chart/pie) after Sales in AppShell.

**2c — Condition & variant on add:** In `web/src/app/search/page.tsx` add modal, add a Condition select (Raw, NM, LP, MP, HP, DMG) and Variant select (Normal, Holofoil, Reverse Holo, 1st Edition); send `condition` and `variant` in `addHolding`. Show variant as a badge on the collection tile + card detail (small badge next to condition).

**2d — Pack-opening reveal:** a CSS-3D reveal shown after a successful add. Simplest self-contained approach: after `addHolding` succeeds on the search page, instead of immediately routing, show a full-screen reveal overlay: a "booster" panel that, on mount, plays a short CSS animation (glow + a 3D flip using `transform: rotateY` with `transform-style: preserve-3d`) revealing the added card image with a holo sheen sweep, then a "Done"/auto-continue to `/`. Reduced-motion → show the card immediately with no flip. Skippable (click to continue). Keep it ~1.5–2s. New component `web/src/components/PackReveal.tsx` + CSS in globals.

- Verify tsc/lint/build after each sub-part; commit per sub-part or grouped. 

---

## Self-review checklist
- set_progress only counts distinct owned card_ids per set; handles missing set_total; allocation sums to total_value; top_cards sorted desc.
- FX cached, wrapped, 502 on failure; frontend falls back to USD when rate null.
- Currency toggle persists, converts money app-wide where wired, reduced-motion irrelevant; no SSR localStorage read in render.
- variant persisted + shown; add modal sends it.
- Pack reveal reduced-motion safe, skippable, doesn't trap the user; only on successful add.
- Nav +1 (Insights) only; light/dark/mobile intact.
