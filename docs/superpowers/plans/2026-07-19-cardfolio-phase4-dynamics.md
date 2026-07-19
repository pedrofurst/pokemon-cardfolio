# Cardfolio Phase 4 (Dynamics & Signals) Implementation Plan

**Goal:** Make the app work for you (auto daily refresh), show the payoff of stored history (animated trend charts), and answer "am I overpaying?" at buy time — with a tasteful motion layer.

**Architecture:** Same 4 layers. A `PortfolioSnapshot` captures total value/cost/pnl at each refresh so we can chart value-over-time. An in-process scheduler (APScheduler) runs a daily refresh + portfolio snapshot, gated by settings (off in tests). A `PriceCheckService` compares an offer price to live/stored market. Frontend gains hand-rolled animated SVG charts, a count-up number, staggered reveals, and a fair-price gauge — all reduced-motion safe.

**Tech stack:** Python/FastAPI/SQLModel/httpx/APScheduler/pytest/respx; Next.js 16/TS.

## Global constraints
- Python 3.11+; TS. USD only.
- External HTTP only in providers/ (wrapped → typed errors); services bubble; routers translate → HTTP (global handlers exist).
- `owner_id` on new rows. Tests never hit real network; scheduler MUST be disabled in tests.
- All motion respects `prefers-reduced-motion`; keep it restrained (≤ ~600ms, ease-out).
- Don't regress the 55 existing backend tests.

---

### BT1: Portfolio snapshots + resilient refresh + history endpoints

**Files:** `backend/app/models.py` (+`PortfolioSnapshot`), new `backend/app/repositories/portfolio_repository.py`, `backend/app/services/price_service.py` (resilient refresh), `backend/app/services/collection_service.py` (+`record_portfolio_snapshot`), `backend/app/routers/prices.py` (record on refresh + status), new `backend/app/routers/history.py`, `backend/app/deps.py`, `backend/app/main.py`; tests.

Produces:
- `PortfolioSnapshot(id, owner_id="me", total_cost, total_value, pnl, fetched_at=now(utc))`.
- `PortfolioRepository(session)`: `add(snap)`, `history(owner_id)->list` (asc by fetched_at), `latest(owner_id)->PortfolioSnapshot|None`.
- `PriceService.refresh_prices` becomes **resilient**: wrap each card's `provider.get_price` in try/except (this is the ONE allowed exception to "services don't catch" — justify inline: a scheduled batch must not abort on one bad card); collect failures; still write snapshots for the ones that succeed; return `{"written": n, "failed": m}` (update the router + existing tests for the new return shape — keep it backward-friendly by returning a dict).
- `CollectionService.record_portfolio_snapshot(owner_id="me")->PortfolioSnapshot`: compute `summary()` and persist a PortfolioSnapshot via portfolio_repo (inject `portfolio_repo` into CollectionService or pass session — prefer injecting a `PortfolioRepository`; update deps + tests).
- `POST /prices/refresh`: after refreshing, also record a portfolio snapshot; return `{written, failed}`.
- `GET /prices/status` → `{last_refresh: iso|null}` (from latest price snapshot or portfolio snapshot).
- `GET /history/portfolio` → `[{fetched_at, total_value, total_cost, pnl}]`.
- `GET /history/card/{card_id}` → `[{fetched_at, market_price}]` (from PriceRepository.history).

Tests: PortfolioSnapshot repo add/history; refresh with one failing card still writes the others and reports failed≥1; record_portfolio_snapshot writes totals; history endpoints return seeded series. Commit.

---

### BT2: Scheduler + price-check

**Files:** `backend/pyproject.toml` (+apscheduler), `backend/app/config.py` (+`enable_scheduler: bool = True`, `refresh_interval_hours: int = 24`), `backend/app/scheduler.py` (new), `backend/app/main.py` (start/stop in lifespan), new `backend/app/services/price_check_service.py`, new `backend/app/routers/price_check.py`, `backend/app/deps.py`; tests.

Produces:
- `scheduler.py`: builds an APScheduler `BackgroundScheduler`, adds a daily job (`refresh_interval_hours`) that opens a session, runs `PriceService.refresh_prices("me")` then `CollectionService.record_portfolio_snapshot("me")`, with its own try/except + no crash. Expose `start_scheduler()`/`shutdown_scheduler()`.
- `main.py` lifespan: if `get_settings().enable_scheduler`, start scheduler after `init_db()`; shut it down on exit. **Tests must set `enable_scheduler=False`** — add that to `tests/conftest.py` (e.g. set env `CARDFOLIO_ENABLE_SCHEDULER=0` / monkeypatch settings) so no scheduler/thread/network starts during tests.
- `PriceCheckService(provider, price_repo)` with `check(card_id, offer_price)->PriceCheckResult`:
  - `PriceCheckResult(card_id, offer, market, low, direct_low, verdict, delta_pct, detail)`.
  - Resolve current price: try `provider.get_price(card_id)` (fresh, full detail); on `PriceProviderError`/`CardNotFoundError` fall back to `price_repo.latest_for(card_id)` if present; if neither → raise the domain error (router translates).
  - `delta_pct = (offer - market)/market*100`.
  - verdict: `offer <= (direct_low or market)*0.9` or `delta_pct <= -15` → "great_deal"; `abs(delta_pct) <= 10` → "fair"; `delta_pct >= 15` → "overpriced"; else "slightly_high"/"slightly_low" (pick: delta_pct>0 → "slightly_high" else "slightly_low"). detail = human sentence.
- `POST /price-check` body `{card_id: str, offer_price: float (ge=0)}` → result dict. (Frontend sends card_id from a search selection.)

Tests: price-check great_deal / fair / overpriced via a fake provider; fallback to snapshot when provider raises; 422 on negative offer. Scheduler: assert `create_application()` with scheduler disabled starts cleanly (no thread) and existing tests still pass. Commit.

---

### FT1: Motion + chart primitives

**Files:** new `web/src/components/TrendChart.tsx`, `web/src/components/CountUp.tsx`, `web/src/components/Reveal.tsx`; `web/src/app/globals.css` (motion utilities); `web/src/lib/api.ts` + `types.ts` (new endpoints/types).

- `TrendChart({ points: {t:string; v:number}[], height?, accent? })`: hand-rolled SVG. Compute a polyline over min/max; render an area fill (holo/accent gradient, low opacity) + a 2px line + a dot on the last point. **Draw-on animation:** animate the line via `stroke-dasharray/`stroke-dashoffset` from full→0 on mount (CSS transition or keyframe); fade the area in. Empty/1-point → show a flat baseline with a muted "not enough history yet" note. Reduced-motion → no draw animation. Keep it dependency-free.
- `CountUp({ value, format })`: animates from previous value to `value` using requestAnimationFrame over ~500ms ease-out; `format` maps number→string (e.g. money). On first mount animate from 0. Reduced-motion → render final immediately. Guard against non-finite.
- `Reveal({ children, index? })`: wraps content; applies a CSS entrance (fade + 8px translateY) with `animation-delay: calc(index * 45ms)`; reduced-motion → no transform/opacity animation.
- globals.css: keyframes `reveal-in`, `.reveal`, `.spin` (rotation for refresh icon while active), `.value-flash-up/.value-flash-down` (brief bg flash), and the chart classes. All wrapped so `@media (prefers-reduced-motion: reduce)` disables transforms/animations.
- api.ts/types.ts: `getPortfolioHistory()`, `getCardHistory(id)`, `checkPrice(payload)`, `getPriceStatus()`; types `PortfolioPoint {fetched_at; total_value; total_cost; pnl}`, `PricePoint {fetched_at; market_price}`, `PriceCheckResult {card_id; offer; market; low; direct_low; verdict; delta_pct; detail}`, `PriceStatus {last_refresh: string|null}`.

Commit after tsc/lint/build clean.

---

### FT2: Wire dynamics into Collection + Card detail

**Files:** `web/src/app/page.tsx`, `web/src/app/card/[id]/page.tsx`.

- Collection hero: `CountUp` the total value + P&L; add a small portfolio `TrendChart` (from `getPortfolioHistory`) inside/under the slab (holo accent). Show `last_refresh` ("updated 2h ago" style, simple relative or date) near the Refresh button; while refreshing, add `.spin` to the refresh icon. Stagger the holdings grid with `Reveal index`.
- Card detail: add a per-card `TrendChart` from `getCardHistory(card_id)` above/below the ledger. Reveal the panels.
- Keep all existing data flow. tsc/lint/build clean. Commit.

---

### FT3: Price-check page

**Files:** new `web/src/app/price-check/page.tsx`; `web/src/components/AppShell.tsx` (+nav item, icon = tag/scale); `web/src/app/globals.css` (gauge styles).

- `/price-check` ("use client"): a search box (reuse `api.searchCards`) → pick a card → enter the asking price → call `api.checkPrice({card_id, offer_price})`.
- Result: a **verdict** badge (Great deal / Fair / Slightly high/low / Overpriced) colored via existing semantics (great_deal→gain, overpriced→loss, fair→brand, slight→gold), the `detail` sentence, and an **animated gauge**: a horizontal track marking low → market → high with a needle/marker that animates to the offer's position; delta_pct shown. Reduced-motion → needle appears without transition.
- Add nav item "Price check" to the sidebar (between Search and Watchlist).
- tsc/lint/build clean. Commit.

---

## Self-review checklist
- Scheduler disabled in tests; refresh resilient (per-card isolation) and records a portfolio snapshot; history + status endpoints correct.
- Price-check verdict thresholds correct; falls back to snapshot; 422 on negative.
- Charts animate on mount, degrade to flat/empty gracefully, reduced-motion safe; count-up handles updates + reduced-motion; reveals staggered not janky.
- Motion is restrained (no gratuitous looping); everything reachable; light/dark/mobile intact.
