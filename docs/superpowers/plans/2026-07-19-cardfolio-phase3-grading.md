# Cardfolio Phase 3 (Grading ROI) Implementation Plan

**Goal:** Help decide whether to grade a raw card: compare expected graded net proceeds (PSA 10/9, minus grading cost and selling fees, weighted by grade probability) against selling it raw.

**Architecture:** A stateless `GradingService.evaluate(...)` in the application layer computes the analysis from inputs. Graded prices are entered manually (no graded-price API available); a `GradedPriceProvider` Protocol + a `NullGradedPriceProvider` are defined so PriceCharting/PokeTrace can be plugged in later without touching the service. Optional `card_id` auto-fills the raw price from the latest stored snapshot. One `POST /grading/evaluate` endpoint + a `/grading` frontend page.

**Tech stack:** Python/FastAPI/SQLModel/pytest; Next.js 16/TS. No new DB tables (stateless).

## Global constraints
- Python 3.11+; TS frontend. USD only.
- No network at evaluate time (graded prices are supplied in the request; raw auto-fill reads stored snapshots only).
- Services let errors bubble; routers translate → HTTP (global handlers exist). Pure calculation, typed dataclasses.
- Tests never hit real network. Reuse `.venv`. Don't regress the 43 existing tests.
- YAGNI: no persistence of grading estimates in this phase.

---

### Task 1: GradingService + graded-price interface (calculation core)

**Files:** new `backend/app/providers/graded_base.py`, `backend/app/providers/graded_null.py`, `backend/app/services/grading_service.py`; test `backend/tests/test_grading_service.py`.

**Interfaces produced:**
- `graded_base.GradedPrices(psa10: float | None, psa9: float | None, source: str)` dataclass and `GradedPriceProvider` Protocol: `get_graded_prices(card_id: str) -> GradedPrices | None`.
- `graded_null.NullGradedPriceProvider` implementing it, `get_graded_prices` returns `None` (placeholder for a future real source).
- `grading_service.GradingInput(raw_price: float, psa10_price: float | None, psa9_price: float | None, grading_cost: float = 25.0, selling_fees_pct: float = 13.0, prob_psa10: float = 0.5)`.
- `grading_service.GradingResult(raw_net: float, psa10_net: float | None, psa9_net: float | None, expected_graded_net: float | None, uplift: float | None, roi_pct: float | None, recommendation: str, rationale: str)`.
- `GradingService()` (no deps needed for calc; keep constructor param-free for now) with `evaluate(input: GradingInput) -> GradingResult`.

**Calculation (define exactly):**
- `fees = selling_fees_pct / 100` (clamp/validate at router; service assumes valid).
- `raw_net = raw_price * (1 - fees)`.
- `psa10_net = psa10_price * (1 - fees) - grading_cost` if `psa10_price` not None else None.
- `psa9_net = psa9_price * (1 - fees) - grading_cost` if `psa9_price` not None else None.
- `expected_graded_net`:
  - if both psa10_net and psa9_net not None: `prob_psa10 * psa10_net + (1 - prob_psa10) * psa9_net`.
  - elif only psa10_net not None: `psa10_net` (treat as the only graded outcome).
  - elif only psa9_net not None: `psa9_net`.
  - else: None.
- `uplift = expected_graded_net - raw_net` if expected_graded_net not None else None.
- `roi_pct = (uplift / grading_cost * 100)` if uplift not None and grading_cost > 0 else None.
- `recommendation`:
  - if expected_graded_net is None → "INSUFFICIENT_DATA", rationale "Enter at least a PSA 10 (or PSA 9) price".
  - elif uplift > 0 → "GRADE", rationale like "Expected graded net ${eg:.2f} beats raw ${raw:.2f} by ${uplift:.2f}".
  - else → "DONT_GRADE", rationale "Raw net ${raw:.2f} >= expected graded net ${eg:.2f}; grading not worth the cost".

**Steps:**
- [ ] Create `graded_base.py` (dataclass + Protocol) and `graded_null.py`.
- [ ] Write `test_grading_service.py` FIRST: a clear GRADE case (raw 50, psa10 300, psa9 120, cost 25, fees 13%, prob 0.5 → uplift positive, recommendation "GRADE"); a DONT_GRADE case (raw 200, psa10 210 → uplift negative); INSUFFICIENT_DATA when both graded prices None; verify only-psa10 path; verify roi_pct math on one case.
- [ ] Implement `grading_service.py` exactly per the formulas.
- [ ] Run `python -m pytest`, commit "feat(phase3): grading ROI service + graded-price provider interface".

---

### Task 2: Router + DI + raw-price auto-fill

**Files:** new `backend/app/routers/grading.py`; modify `backend/app/deps.py`, `backend/app/main.py`; test `backend/tests/test_routers.py`.

**Interfaces produced (HTTP):**
- `deps.get_grading_service()` → `GradingService()`. (No provider wired into the calc; the Null provider exists but is not used by evaluate in this phase.)
- `POST /grading/evaluate` body:
  ```json
  {"card_id": "base1-4"|null, "raw_price": 50.0|null, "psa10_price": 300.0|null,
   "psa9_price": 120.0|null, "grading_cost": 25.0, "selling_fees_pct": 13.0, "prob_psa10": 0.5}
  ```
  Behavior: if `raw_price` is null and `card_id` is provided, auto-fill `raw_price` from the latest snapshot's `market_price` for that card via `PriceRepository.latest_for` (needs a session-scoped repo — wire `PriceRepository` into the router via a `get_price_repository`-style dependency or inline using `get_session`). If after auto-fill `raw_price` is still None → HTTP 400 "raw_price required (or a card_id with a stored price)". Validate `selling_fees_pct` in [0,100) and `prob_psa10` in [0,1] and `grading_cost >= 0` via Pydantic Field constraints → 422 on violation. Then call `service.evaluate(GradingInput(...))` and return the `GradingResult` as a dict (`result.__dict__`).

**Steps:**
- [ ] Add `get_grading_service` to deps.py. For raw auto-fill, in the router take `session = Depends(get_session)` and build `PriceRepository(session)` (or add a `get_price_repository` dep). Keep the router thin — only orchestration + the 400 guard.
- [ ] Create `grading.py` with a Pydantic `GradingRequest` (fields + constraints above; `card_id`, `raw_price`, `psa10_price`, `psa9_price` optional; `grading_cost` default 25.0 ge=0; `selling_fees_pct` default 13.0 ge=0 lt=100; `prob_psa10` default 0.5 ge=0 le=1).
- [ ] Register the router in main.py.
- [ ] Tests (existing override pattern): POST with explicit raw+psa10 returns a GRADE/DONT result with expected fields; POST with `card_id` and null raw_price auto-fills from a seeded snapshot; POST with no raw_price and no card_id → 400; an out-of-range `prob_psa10` → 422.
- [ ] Run pytest, commit "feat(phase3): grading evaluate endpoint with raw-price auto-fill".

---

### Task 3: Frontend — Grading page

**Files:** modify `web/src/lib/types.ts`, `web/src/lib/api.ts`; new `web/src/app/grading/page.tsx`; modify `web/src/app/page.tsx` (nav link), and add a "Grade?" link from `web/src/app/card/[id]/page.tsx` that deep-links to `/grading?card_id=...`.

**Interfaces:**
- types.ts: `GradingResult { raw_net:number; psa10_net:number|null; psa9_net:number|null; expected_graded_net:number|null; uplift:number|null; roi_pct:number|null; recommendation:string; rationale:string }`.
- api.ts: `evaluateGrading(payload: Record<string, unknown>): Promise<GradingResult>` (POST /grading/evaluate).

**Steps:**
- [ ] Add the type + api method.
- [ ] `/grading` page ("use client"): a form with inputs (card_id optional/prefilled from `?card_id=` search param via `useSearchParams`, raw_price optional, psa10_price, psa9_price, grading_cost default 25, selling_fees_pct default 13, prob_psa10 default 0.5). On submit, call `evaluateGrading` (send numbers or null for blanks) and render the result: recommendation badge (GRADE/DONT_GRADE/INSUFFICIENT_DATA), rationale, and the net figures. try/catch with an error message (match existing pattern). Wrap the `useSearchParams` usage in a `<Suspense>` boundary as Next 16 requires, or mark accordingly to keep the build clean.
- [ ] home page: add a nav link to `/grading`. card detail page: add a link "Grade?" → `/grading?card_id={card_id}`.
- [ ] `cd web && npx tsc --noEmit && npm run lint && npm run build` clean (raw <img> warnings OK). Commit "feat(phase3): grading page + nav/deep-link".

---

## Self-review checklist
- Calc formulas match the spec exactly; recommendation branches (GRADE/DONT_GRADE/INSUFFICIENT_DATA) covered by tests; roi_pct guarded when grading_cost 0.
- Provider interface + null impl present; evaluate uses request-supplied prices (no network).
- Router validates ranges (422) and the raw-required case (400); auto-fill reads only stored snapshots.
- Frontend builds; grading reachable from nav and from a card's detail page.
