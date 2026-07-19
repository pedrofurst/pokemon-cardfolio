# Cardfolio Phase 5 (Realized P&L, Digest, Animations) Plan

**Goal:** (1) Log sales → realized P&L. (2) A "Today" digest that synthesizes the signals. (3) A tasteful animation pack (holo tilt, price flash, skeletons, toasts, page transitions).

**Tech stack:** Python/FastAPI/SQLModel/pytest; Next 16/TS. No new backend deps.

## Global constraints
- Python 3.11+; TS. USD. `owner_id` on new rows.
- External HTTP only in providers/. Services bubble errors (except the already-justified refresh isolation). Routers translate via existing global handlers.
- Tests never hit real network; scheduler stays off in tests. Don't regress 84 backend tests.
- All motion respects `prefers-reduced-motion`; keep it restrained.

---

### BT1: Sales + realized P&L

**Files:** `backend/app/models.py` (+`Sale`), `backend/app/repositories/holding_repository.py` (+get/update/delete), new `backend/app/repositories/sale_repository.py`, new `backend/app/services/sale_service.py`, new `backend/app/routers/sales.py`, `backend/app/deps.py`, `backend/app/main.py`; tests.

- `Sale(id=_uuid pk, owner_id="me", card_id fk card.id index, quantity int, sale_price float, fee float=0.0, cost_basis float, sold_at datetime=now(utc))`. (sale_price & cost_basis are PER UNIT.)
- `HoldingRepository`: add `get(holding_id)->Holding|None`, `update(holding)->Holding` (add/commit/refresh), `delete(holding_id)->bool`.
- `SaleRepository(session)`: `add(sale)->Sale`, `list(owner_id)->list[Sale]` (desc by sold_at, id tiebreak).
- `SaleService(holding_repo, sale_repo, card_repo)`:
  - `record_sale(holding_id, quantity, sale_price, fee=0.0, owner_id="me") -> Sale`: get holding (raise `ValueError` if missing or not owner); validate `1 <= quantity <= holding.quantity` (raise ValueError otherwise); create Sale(card_id=holding.card_id, quantity, sale_price, fee, cost_basis=holding.acquisition_cost, owner_id); reduce holding.quantity by quantity → if 0 delete holding else update; return the sale.
  - dataclass `RealizedSummary(total_proceeds, total_cost, realized_pnl, sales_count)`; `realized_summary(owner_id="me")->RealizedSummary` where per sale: proceeds = sale_price*quantity - fee; cost = cost_basis*quantity; realized_pnl = Σ(proceeds - cost).
  - `history(owner_id="me")->list[tuple[Sale, Card|None]]`.
- Router `sales.py`: `POST /holdings/{holding_id}/sell` Pydantic `SellRequest {quantity:int Field(ge=1), sale_price:float Field(ge=0), fee:float Field(ge=0)=0}` → `service.record_sale(...)`; on ValueError → HTTP 400 (add a small try/except in the router translating ValueError→400, log once). `GET /sales` → `{summary: RealizedSummary.__dict__, items:[{sale, card}]}`. Register router; add `get_sale_service` to deps.
- Tests: record_sale reduces qty / deletes at 0 / creates Sale with cost_basis; realized_summary math; selling more than held → 400; unknown holding → 400; GET /sales shape. Run `python -m pytest` (all pass). Commit.

---

### BT2: Today digest

**Files:** new `backend/app/services/digest_service.py`, new `backend/app/routers/digest.py`, `backend/app/deps.py`, `backend/app/main.py`; tests.

- `DigestService(collection_service, opportunity_service, sale_service, portfolio_repo)`:
  - `build(owner_id="me") -> dict` with:
    - `summary`: CollectionSummary.__dict__ (value/cost/pnl/pnl_pct).
    - `realized`: RealizedSummary.__dict__.
    - `top_gainer` / `top_loser`: from `collection_service.list_collection` sorted by pnl desc/asc → the top one each as `{card_id, card_name, pnl, current_price}` (or null if empty).
    - `movers` / `deals` / `target_hits`: from `opportunity_service.all()` — include counts and the top 3 of each (Signal dicts).
    - `last_refresh`: latest portfolio snapshot fetched_at iso or null.
- Router `digest.py`: `GET /digest` → `service.build()`. Register; add `get_digest_service` to deps (compose the other services with a shared session).
- Tests: seed holdings + a mover + a sale → digest returns summary, realized, top_gainer, and mover present. Run pytest. Commit.

---

### FT1: Animation primitives

**Files:** new `web/src/components/TiltCard.tsx`, `web/src/components/Skeleton.tsx`, `web/src/components/Toast.tsx` (ToastProvider + useToast), `web/src/app/template.tsx` (page transition), `web/src/app/globals.css` (tilt/flash/shimmer/toast keyframes), `web/src/app/layout.tsx` (wrap in ToastProvider).

- `TiltCard`: "use client" wrapper. On pointer move over the element, compute rotateX/rotateY (max ~6deg) via CSS transform + a moving radial "glare" overlay (holo) following the cursor; reset on leave. Respect reduced-motion (no transform/glare). Props: `{children, className?}`. Use CSS custom props (`--rx`,`--ry`,`--mx`,`--my`) set via a ref + rAF-throttled handler; keep it cheap. Don't break the tile being a link (pointer events must still click through).
- `Skeleton`: simple shimmer blocks — `<Skeleton style/className>` and a `SkeletonCardGrid`/`SkeletonSlab` helper for the collection loading state. CSS shimmer keyframe.
- `Toast.tsx`: `ToastProvider` (context, holds a queue), `useToast()` returning `toast(message, tone?: 'ok'|'error')`. Render toasts fixed bottom-right, slide-in + auto-dismiss ~2.5s. Reduced-motion → no slide, just fade/appear.
- `app/template.tsx`: wraps children in a div with a `page-enter` class (fade + 6px slide up) that re-runs on each navigation (template remounts per route). Reduced-motion disables it.
- `layout.tsx`: wrap `<AppShell>` (or its children) with `<ToastProvider>`.
- globals.css: add `@keyframes shimmer`, `.skeleton`, `.tilt` base + glare, `@keyframes flash-up/flash-down` (already present — reuse) + `.flash-up/.flash-down` if missing, `.toast`/`@keyframes toast-in`, `.page-enter`/`@keyframes page-enter`. All disabled under `@media (prefers-reduced-motion: reduce)`.

Verify tsc/lint/build. Commit.

---

### FT2: Apply animations

**Files:** `web/src/app/page.tsx` (collection), `web/src/app/search/page.tsx`.

- Collection: wrap each holding tile's inner card in `TiltCard` (keep the Link). On refresh, diff previous vs new `current_price` per card_id; for changed cards, add `flash-up`/`flash-down` to the tile for ~900ms (store a transient set in state). Replace the `!data` loading state with `SkeletonSlab` + `SkeletonCardGrid`. Keep the ConnectionError path.
- Search: wrap result tiles in `TiltCard`; on Add success show `toast("Added to your collection")` (before redirect) and on Watch show `toast("Added to watchlist")`; on error `toast(..., 'error')`.
- Verify tsc/lint/build. Commit.

---

### FT3: Sell flow + Sales page

**Files:** `web/src/lib/types.ts` + `api.ts` (sell/sales), new `web/src/app/sales/page.tsx`, `web/src/app/card/[id]/page.tsx` (Sell button+modal), `web/src/components/AppShell.tsx` (nav "Sales").

- types: `Sale {id; card_id; quantity; sale_price; fee; cost_basis; sold_at}`, `SaleEntry {sale:Sale; card:{...}|null}`, `RealizedSummary {total_proceeds; total_cost; realized_pnl; sales_count}`, `SalesResponse {summary:RealizedSummary; items:SaleEntry[]}`.
- api: `sellHolding(holdingId, payload)` (POST /holdings/{id}/sell), `getSales()` (GET /sales).
- Card detail: a "Log a sale" button (only when it's an owned holding) → modal (quantity default 1 max holding.quantity, sale price prefilled from current_price, fee) → `sellHolding` → toast("Sale logged") → refresh/redirect to /sales. Handle 400 with a toast.
- `/sales` page: realized P&L summary (proceeds, cost, realized pnl with PnLPill) + a table/list of sales (card, qty, sale price, proceeds, realized per sale). Empty state. ConnectionError handling. Reveal/animations consistent.
- Nav: add "Sales" (icon: receipt/tag) after Grading.
- Verify. Commit.

---

### FT4: Today digest page

**Files:** `web/src/lib/types.ts`+`api.ts` (digest), new `web/src/app/today/page.tsx`, `web/src/components/AppShell.tsx` (nav "Today" near top).

- types: `Digest {summary; realized; top_gainer; top_loser; movers; deals; target_hits; last_refresh}` (loosely typed dicts ok, but define Signal reuse + a `DigestMover` etc. minimal).
- api: `getDigest()`.
- `/today` page: a dashboard — hero-ish summary (value, unrealized + realized P&L), then compact cards: "Top gainer", "Top loser", "Biggest mover", "Best deal", "Targets hit (n)", each linking to the relevant card/page. Empty states when no data. ConnectionError handling. Use CountUp/animations tastefully.
- Nav: add "Today" as the first item (before Collection). Icon: sun/spark.
- Verify. Commit.

---

## Self-review checklist
- Sale math (per-unit cost_basis, proceeds net of fee), qty validation, holding reduce/delete; realized summary correct.
- Digest composes existing services without duplicating logic; handles empty collection.
- Animations restrained + reduced-motion safe; tilt doesn't block tile clicks; flash only on changed prices; toasts auto-dismiss; skeletons match layout.
- All pages keep ConnectionError handling; nav not broken; light/dark/mobile intact.
