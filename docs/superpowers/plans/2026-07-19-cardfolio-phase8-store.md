# Cardfolio Phase 8 (Store / Booster Guide) Plan

**Goal:** A "Store" page: featured booster sets, their chase cards + market values, an ESTIMATED per-pack hit chance, and direct buy links (TCGplayer/eBay search). Informational, clearly labeled as estimates + not-advice + not-affiliated.

**Tech stack:** Python/FastAPI/httpx/pytest; Next 16/TS.

## Global constraints
- External HTTP only in providers/ (wrapped → PriceProviderError). Services bubble; routers translate via global handlers.
- Odds are HEURISTIC estimates (no real pull-rate data exists) — must be labeled as such in the UI. Not financial advice; not affiliated with linked stores.
- Buy links are marketplace SEARCH URLs (no affiliate params), open in a new tab with rel="noopener noreferrer".
- The store aggregates many upstream calls → cache the built result in-process (~6h). Tests never hit the network (mock provider / respx).
- Don't regress 141 backend tests.

---

### BT1: Store backend (provider + service + endpoint)

**Files:** `backend/app/providers/base.py` (+`SetInfo` dataclass), `backend/app/providers/pokemontcgio.py` (+`list_sets`, `get_set_cards`), new `backend/app/services/store_service.py`, new `backend/app/routers/store.py`, deps, main; tests.

- `SetInfo(id: str, name: str, series: str, total: int | None, release_date: str, logo_url: str)`.
- Provider:
  - `list_sets(limit: int = 12) -> list[SetInfo]`: GET `/sets?orderBy=-releaseDate&pageSize={limit}`; map each `{id,name,series, total, releaseDate, images.logo}`. Wrap httpx/parse errors → PriceProviderError.
  - `get_set_cards(set_id: str) -> list[CardResult]`: GET `/cards?q=set.id:{set_id}&pageSize=250`; reuse `_to_card_result`. Wrap errors.
  - (Keep the existing PriceProvider protocol methods; these are additional concrete methods on PokemonTcgIoProvider.)
- `store_service.py`:
  - const `HIT_THRESHOLD_USD = 15.0`; `HIT_RARITIES` = anything NOT in {"", "Common", "Uncommon"} counts as the "rare+ / hit-slot" tier.
  - dataclasses `ChaseCard(id, name, image_url, price, rarity, buy_url)`, `Booster(set_id, set_name, series, release_date, logo_url, total, chase_cards: list[ChaseCard], good_count, hit_pool, est_hit_pct: float|None, one_in: int|None, top_chase_value: float|None, booster_links: dict)`.
  - `StoreService(provider)` with `build(featured: int = 6) -> list[Booster]`:
    - `sets = provider.list_sets(limit=featured*2)` (fetch a few extra in case some have no prices).
    - For each set until we have `featured` boosters: `cards = provider.get_set_cards(set.id)`; `priced = [c for c in cards if c.market_price is not None]`; if `len(priced) == 0`: skip.
      - `chase = sorted(priced, key=market_price desc)[:5]` → ChaseCard each (buy_url: use `c.tcgplayer_id` if it startswith "http" else a tcgplayer search URL for the card name).
      - `hit_pool = [c for c in cards if (c.rarity or "") not in ("", "Common", "Uncommon")]` (the rare+ pool). `good = [c for c in hit_pool if (c.market_price or 0) >= HIT_THRESHOLD_USD]`.
      - `est_hit_pct = round(len(good)/len(hit_pool)*100, 1) if hit_pool else None`; `one_in = round(len(hit_pool)/len(good)) if good else None`.
      - `top_chase_value = chase[0].price`.
      - `booster_links = {"tcgplayer": tcgplayer_search(set.name + " booster"), "ebay": ebay_search(set.name + " booster box")}` where the search builders URL-encode the query: tcgplayer `https://www.tcgplayer.com/search/pokemon/product?productLineName=pokemon&q=...`; ebay `https://www.ebay.com/sch/i.html?_nkw=...`.
    - Cache the built list in-process with `time.monotonic()` TTL ~21600s (6h); expose `clear_store_cache()` for tests.
  - No logging; errors bubble.
- Router `store.py`: `GET /store` → `{"boosters": [dataclasses.asdict(b) for b in service.build()]}`. Register in main.py; add `get_store_service` to deps.py reusing the singleton `_provider`.
- Tests: a fake provider (list_sets returns 2 SetInfo; get_set_cards returns CardResults incl. some priced ≥15, some < 15, some Common) → StoreService.build returns boosters with chase sorted desc, est_hit_pct = good/hit_pool, one_in correct, booster_links contain encoded set name, common cards excluded from hit_pool. Provider mapping via respx (list_sets + get_set_cards). Cache reset between tests. Run `python -m pytest` (all pass). Commit "feat(phase8): store service + booster guide endpoint".

---

### FT1: Store page

**Files:** `web/src/lib/types.ts` (+Booster/ChaseCard), `web/src/lib/api.ts` (+getStore), new `web/src/app/store/page.tsx`, `web/src/components/AppShell.tsx` (nav "Store"), `web/src/app/globals.css` (any store styles), `web/src/components/Skeleton.tsx` (reuse).

- types: `ChaseCard {id;name;image_url;price:number|null;rarity:string;buy_url:string}`, `Booster {set_id;set_name;series;release_date;logo_url;total:number|null;chase_cards:ChaseCard[];good_count:number;hit_pool:number;est_hit_pct:number|null;one_in:number|null;top_chase_value:number|null;booster_links:{tcgplayer:string;ebay:string}}`, `StoreResponse {boosters:Booster[]}`.
- api: `getStore(): Promise<StoreResponse>`.
- `/store` page ("use client"): load pattern with useCallback + ConnectionError. Because the endpoint is slow on first (uncached) load, show a Skeleton grid while loading. PageHead eyebrow "Buy" title "Store" subtitle "Boosters worth a look — chase cards, estimated odds, and where to buy." 
  - A prominent **disclaimer** line/banner: "Odds are rough estimates, not official pull rates. Prices via pokemontcg.io. Not affiliated with any store. Not financial advice."
  - For each booster: a `.panel` card with the set logo (img) + name + release date; the estimated-odds line: `≈ {est_hit_pct}% chance the rare slot is a card worth ${'>='}$15` and `≈ 1 in {one_in} packs` (show "—" if null); the **chase cards** as a small row (image, name, price via `useMoney().fmt`, each linking to its `buy_url` in a new tab); and two **Buy** buttons — "TCGplayer" and "eBay" — linking to `booster_links.*` (target="_blank" rel="noopener noreferrer"). 
  - All external links: `target="_blank" rel="noopener noreferrer"`.
  - Empty/ConnectionError states.
- Nav: add "Store" item (href `/store`, match startsWith("/store")); icon a storefront/bag SVG (18x18 stroke currentColor). Place after "Search & add" or near Price check — your call, keep grouping sensible.
- Verify tsc/lint/build. Commit "feat(phase8): store page (booster guide + buy links)".

---

## Self-review checklist
- Odds clearly labeled as estimates; disclaimer visible; not framed as advice.
- External links open new tab + rel noopener; search URLs encoded; no affiliate params.
- Provider wraps errors; store result cached (6h) so the page isn't slow every load; cache reset in tests.
- Common/Uncommon excluded from hit pool; chase sorted desc; handles sets with no priced cards (skip).
- Frontend shows skeleton while the (slow) endpoint loads; ConnectionError on failure.
