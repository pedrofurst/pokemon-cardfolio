# Cardfolio Phase 2 (Scanner) Implementation Plan

**Goal:** Add a watchlist and derive opportunity signals (movers, deals, target hits) from stored price snapshots, with an Opportunities page.

**Architecture:** Same 4 layers. Extend the provider to capture full TCGplayer price detail; store it on `PriceSnapshot`; a new `OpportunityService` computes signals purely from stored data (no read-time network). New `WatchItem` model + repo. New `/watchlist` and `/opportunities` routers. Frontend adds an Opportunities page and watchlist controls.

**Tech stack:** Python/FastAPI/SQLModel/httpx/pytest/respx; Next.js 16/TS.

## Global constraints
- Python 3.11+; TS frontend. USD only.
- External HTTP only in providers/, wrapped → typed errors; services let errors bubble; routers translate → HTTP + log once (global handlers already registered in main.py).
- `owner_id` on all owned/watched rows (default "me").
- Signals computed from stored snapshots — no network at `/opportunities` read time.
- Tests never hit real network (respx/fakes). Reuse existing `.venv` in backend/.
- Do not regress the 22 existing tests.

---

### Task 1: Richer price capture (provider + snapshot + refresh)

**Files:** modify `backend/app/providers/base.py`, `backend/app/providers/pokemontcgio.py`, `backend/app/models.py`, `backend/app/services/price_service.py`, `backend/app/services/collection_service.py`; tests in `backend/tests/test_provider.py`, `test_price_service.py`.

**Interfaces produced:**
- `PriceResult` gains `low: float|None, mid: float|None, high: float|None, direct_low: float|None` (keep `market_price: float`, `currency`, `source`, `card_id`).
- `PriceSnapshot` gains nullable columns `low, mid, high, direct_low` (default None).
- Provider populates all fields; `refresh_prices` and the add-path snapshot store them.

Steps:
- [ ] In `base.py`, add the four optional fields to `PriceResult` (all `float | None = None`).
- [ ] In `pokemontcgio.py`, add `_extract_prices(card) -> dict` that returns `{market, low, mid, high, direct_low}` from the FIRST tcgplayer variant that has a non-None `market` (map camelCase `directLow`→`direct_low`, `low/mid/high/market` straight). Keep `_extract_market_price` behavior (still used to detect "no price"). Update `get_price` to build `PriceResult(card_id, market_price=market, currency="USD", source="tcgplayer", low=..., mid=..., high=..., direct_low=...)`. `search_cards`/`CardResult` unchanged (search stays market-only).
- [ ] In `models.py`, add `low/mid/high/direct_low: float | None = None` to `PriceSnapshot`.
- [ ] In `price_service.refresh_prices`, store the new fields on the snapshot.
- [ ] In `collection_service.add_holding_from_result`, the snapshot currently uses `result.market_price` (search has no low/mid/high) — leave those extra fields None on the add-path snapshot (only refresh captures full detail). No behavior change to P&L.
- [ ] Tests: extend a provider respx test so a card JSON with `tcgplayer.prices.holofoil={low,mid,high,market,directLow}` yields a `PriceResult` with `direct_low` mapped correctly; a price_service test that a refreshed snapshot persists `direct_low`.
- [ ] Run `python -m pytest`, commit.

---

### Task 2: Watchlist model + repository + refresh coverage

**Files:** `backend/app/models.py` (add `WatchItem`), new `backend/app/repositories/watch_repository.py`, modify `backend/app/services/price_service.py`; tests `backend/tests/test_repositories.py`, `test_price_service.py`.

**Interfaces produced:**
- `WatchItem(id=uuid pk, owner_id="me", card_id→card.id indexed, target_price: float|None=None, created_at=now(utc))`.
- `WatchRepository(session)`: `add(item)->WatchItem`, `list(owner_id)->list[WatchItem]`, `get(item_id)->WatchItem|None`, `delete(item_id)->bool`, `card_ids(owner_id)->set[str]`.
- `PriceService.__init__` gains a `watch_repo: WatchRepository` param (append it last, default not allowed — update all constructions in deps.py + tests). `refresh_prices` refreshes owned ∪ watched card_ids.

Steps:
- [ ] Add `WatchItem` to models.py (import timezone already present).
- [ ] Create `watch_repository.py` mirroring the existing repo style (constructor takes `session`; methods above; `card_ids` returns a set).
- [ ] Update `PriceService` to accept `watch_repo` and union watched card_ids into the refresh loop; dedupe so a card that is both owned and watched is refreshed once.
- [ ] Update `deps.get_price_service` and every `PriceService(...)` construction in tests to pass a `WatchRepository`.
- [ ] Tests: repo add/list/delete/card_ids; a refresh test where a watched (not owned) card gets a snapshot.
- [ ] Run pytest, commit.

---

### Task 3: OpportunityService (signals from snapshots)

**Files:** new `backend/app/services/opportunity_service.py`; test `backend/tests/test_opportunity_service.py`.

**Interfaces produced:**
- Dataclasses: `Signal(kind: str, card_id: str, card_name: str, detail: str, current_price: float|None, reference_price: float|None, change_pct: float|None)`.
- `OpportunityService(card_repo, price_repo, holding_repo, watch_repo)` with:
  - `movers(owner_id="me", threshold_pct=10.0) -> list[Signal]`: for each card in owned∪watched, take the two most recent snapshots; if both exist and `abs((latest.market-prev.market)/prev.market*100) >= threshold_pct`, emit a `Signal(kind="mover", change_pct=..., current_price=latest.market, reference_price=prev.market, detail="+X% since last refresh")`.
  - `deals(owner_id="me", threshold_pct=15.0) -> list[Signal]`: for each card in owned∪watched, latest snapshot; if `direct_low` not None and `direct_low <= market*(1-threshold_pct/100)`, emit `Signal(kind="deal", current_price=direct_low, reference_price=market, change_pct=discount%, detail="cheapest listing X% under market")`.
  - `target_hits(owner_id="me") -> list[Signal]`: for each `WatchItem` with `target_price` not None, latest snapshot market ≤ target → `Signal(kind="target", current_price=market, reference_price=target_price, detail="hit target $T")`.
  - `all(owner_id="me", mover_pct=10.0, deal_pct=15.0) -> dict` returning `{"movers":[...], "deals":[...], "target_hits":[...]}`.
- Needs `PriceRepository.latest_two(card_id) -> list[PriceSnapshot]` (most recent first, ≤2) — add it to price_repository.py.

Steps:
- [ ] Add `PriceRepository.latest_two(card_id)`.
- [ ] Write `test_opportunity_service.py` first (TDD): seed cards + snapshots via repos, assert a 20% jump appears in movers; a direct_low 30% under market appears in deals; a watchlist target hit appears in target_hits; sub-threshold changes do NOT appear.
- [ ] Implement `opportunity_service.py`. Compute owned∪watched card set from holding_repo + watch_repo. Guard div-by-zero (prev.market==0 → skip mover). `card_name` via card_repo.get.
- [ ] Run pytest, commit.

---

### Task 4: Routers (watchlist + opportunities) + DI

**Files:** new `backend/app/routers/watchlist.py`, `backend/app/routers/opportunities.py`; modify `backend/app/deps.py`, `backend/app/main.py`; test `backend/tests/test_routers.py` (add cases).

**Interfaces produced (HTTP):**
- `deps.get_opportunity_service` (wires the 4 repos).
- `GET /watchlist` → `[{item, card}]`; `POST /watchlist` body `{card: CardPayload (same shape as holdings), target_price: float|None}` → upserts card + creates WatchItem, returns it; `DELETE /watchlist/{item_id}` → `{deleted: bool}`.
- `GET /opportunities?mover_pct=&deal_pct=` → `{movers, deals, target_hits}` (each a list of Signal dicts).

Steps:
- [ ] Add `get_opportunity_service` to deps.py (reuse existing singleton provider; opportunity service needs no provider).
- [ ] Create `watchlist.py`: reuse a `CardPayload` (import/replicate the one from holdings.py — factor `CardPayload` into a small shared module `backend/app/routers/schemas.py` and import in both holdings.py and watchlist.py to avoid duplication). POST upserts the card via CardRepository then adds WatchItem via WatchRepository (do this in a small `WatchService` OR inline in a service method — prefer a `CollectionService`-style method; simplest: add `add_watch_from_result(result, target_price, owner_id)` to a new tiny `WatchService`, but to avoid over-engineering, put card upsert + watch add in `OpportunityService.add_watch(...)` and `list_watch(...)`/`remove_watch(...)`). Choose ONE home and keep routers thin.
- [ ] Create `opportunities.py`: `GET /opportunities` calls `service.all(mover_pct, deal_pct)` and returns the dict of Signal dicts (`[s.__dict__ for s in ...]`).
- [ ] Register both routers in main.py.
- [ ] Tests: POST /watchlist then GET returns it; DELETE removes it; GET /opportunities returns the three keys (seed a mover via two snapshots and assert it appears through the HTTP layer).
- [ ] Run pytest, commit.

---

### Task 5: Frontend — Opportunities page + watchlist controls

**Files:** modify `web/src/lib/types.ts`, `web/src/lib/api.ts`; new `web/src/app/opportunities/page.tsx`, `web/src/app/watchlist/page.tsx`; modify `web/src/app/search/page.tsx` (add "Watch" button) and `web/src/app/page.tsx` (nav links).

**Interfaces:**
- types.ts: `Signal`, `OpportunitiesResponse {movers:Signal[]; deals:Signal[]; target_hits:Signal[]}`, `WatchEntry {item:{id,card_id,target_price}, card:{id,name,set_name,image_url}|null}`.
- api.ts: `listOpportunities(moverPct?, dealPct?)`, `listWatchlist()`, `addWatch(payload)`, `removeWatch(id)`.

Steps:
- [ ] Add the types and api methods.
- [ ] `/opportunities` page: fetch on mount, render three sections (Movers, Deals, Target hits), each listing card name + detail + prices; empty-state text per section.
- [ ] `/watchlist` page: list watched cards with remove buttons; a note that target price shows if set.
- [ ] search page: add a "Watch" button next to "Add" that calls `api.addWatch({card, target_price:null})`.
- [ ] home page: add nav links to `/search`, `/watchlist`, `/opportunities`.
- [ ] `cd web && npx tsc --noEmit && npm run lint && npm run build` clean (raw <img> warnings OK). Commit.

---

## Self-review checklist
- Provider extra-field mapping tested; snapshot stores them; refresh covers watched cards.
- Opportunity logic covers movers/deals/target_hits with threshold boundaries tested; div-by-zero guarded.
- Routers thin; card upsert on watch add; DELETE idempotent; DI wired; global error handlers still cover new routers.
- No read-time network in `/opportunities`.
- Frontend builds; nav reachable.
