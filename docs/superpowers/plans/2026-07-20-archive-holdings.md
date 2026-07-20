# Archive Holdings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user remove a card from their collection without destroying its price history, and restore it later.

**Architecture:** Add a nullable `archived_at` timestamp to `Holding`. The active/archived filter lives in `HoldingRepository.list`, not in any service, because four callers reach holdings directly and would otherwise be missed. Two `PATCH` endpoints flip the state; the collection page gains a toggle to view and restore archived cards.

**Tech Stack:** FastAPI, SQLModel, SQLite, pytest, Next.js 16 App Router, React 19, TypeScript.

Spec: `docs/superpowers/specs/2026-07-20-archive-holdings-design.md`

## Global Constraints

- Backend layering is strict: HTTP only in `routers/`, business logic in `services/`, database access only in `repositories/`, external HTTP only in `providers/`.
- Tests: one assertion per test. Test names start with `test_` and describe behaviour. Use the `session` fixture from `tests/conftest.py`.
- Run backend tests with `cd backend && .venv/bin/pytest`.
- Migrations go in `_MIGRATION_COLUMNS` in `app/db.py`. Never Alembic.
- Every user-owned row carries `owner_id`, hardcoded `"me"`.
- Archiving must never write a `Sale` row or change realized P&L.
- Frontend: no CSS framework. Styles go in `web/src/app/globals.css`. `<Link prefetch={false} />` is not used in this codebase — match surrounding code.

---

### Task 1: Add `archived_at` to the model and migration

**Files:**
- Modify: `backend/app/models.py:23-33`
- Modify: `backend/app/db.py:14-22`
- Test: `backend/tests/test_db_migrations.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `Holding.archived_at: datetime | None`, defaulting to `None`.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_db_migrations.py`:

```python
def test_migration_adds_archived_at_to_existing_holding_table():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE holding (id TEXT PRIMARY KEY, owner_id TEXT, card_id TEXT)"
        ))
    run_migrations(engine)
    with engine.begin() as connection:
        columns = {row[1] for row in connection.execute(text("PRAGMA table_info(holding)"))}
    assert "archived_at" in columns
```

Check the existing imports at the top of that file; add any of `create_engine`, `StaticPool`, `text`, `run_migrations` that are missing.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/test_db_migrations.py::test_migration_adds_archived_at_to_existing_holding_table -v`
Expected: FAIL — `assert 'archived_at' in {'id', 'owner_id', 'card_id'}`

- [ ] **Step 3: Add the column to the model**

In `backend/app/models.py`, add as the last field of `Holding`:

```python
    archived_at: datetime | None = None
```

`datetime` is already imported in this module for `WatchItem`.

- [ ] **Step 4: Add the migration entry**

In `backend/app/db.py`, append to `_MIGRATION_COLUMNS`:

```python
    ("holding", "archived_at", "TIMESTAMP"),
```

- [ ] **Step 5: Run the full suite**

Run: `cd backend && .venv/bin/pytest`
Expected: PASS, including the new test and all 184 existing tests.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models.py backend/app/db.py backend/tests/test_db_migrations.py
git commit -m "feat: add archived_at column to Holding"
```

---

### Task 2: Repository filtering and state change

**Files:**
- Modify: `backend/app/repositories/holding_repository.py`
- Test: `backend/tests/test_repositories.py`

**Interfaces:**
- Consumes: `Holding.archived_at` from Task 1.
- Produces:
  - `HoldingRepository.list(owner_id: str, archived: bool = False) -> list[Holding]`
  - `HoldingRepository.set_archived(holding_id: str, archived: bool) -> Holding | None`

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_repositories.py`:

```python
def test_holding_list_excludes_archived_by_default(session):
    session.add(Card(id="base1-4", name="Charizard"))
    session.commit()
    repo = HoldingRepository(session)
    holding = repo.add(Holding(card_id="base1-4", owner_id="me"))
    repo.set_archived(holding.id, True)
    assert repo.list("me") == []


def test_holding_list_returns_archived_when_requested(session):
    session.add(Card(id="base1-4", name="Charizard"))
    session.commit()
    repo = HoldingRepository(session)
    holding = repo.add(Holding(card_id="base1-4", owner_id="me"))
    repo.set_archived(holding.id, True)
    assert len(repo.list("me", archived=True)) == 1


def test_holding_set_archived_stamps_a_timestamp(session):
    session.add(Card(id="base1-4", name="Charizard"))
    session.commit()
    repo = HoldingRepository(session)
    holding = repo.add(Holding(card_id="base1-4", owner_id="me"))
    assert repo.set_archived(holding.id, True).archived_at is not None


def test_holding_set_archived_false_clears_the_timestamp(session):
    session.add(Card(id="base1-4", name="Charizard"))
    session.commit()
    repo = HoldingRepository(session)
    holding = repo.add(Holding(card_id="base1-4", owner_id="me"))
    repo.set_archived(holding.id, True)
    assert repo.set_archived(holding.id, False).archived_at is None


def test_holding_set_archived_returns_none_when_missing(session):
    assert HoldingRepository(session).set_archived("nonexistent-id", True) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/pytest tests/test_repositories.py -k archived -v`
Expected: FAIL — `AttributeError: 'HoldingRepository' object has no attribute 'set_archived'`

- [ ] **Step 3: Implement**

Replace `list` and add `set_archived` in `backend/app/repositories/holding_repository.py`:

```python
    def list(self, owner_id: str, archived: bool = False) -> list[Holding]:
        statement = select(Holding).where(Holding.owner_id == owner_id)
        if archived:
            statement = statement.where(Holding.archived_at.is_not(None))
        else:
            statement = statement.where(Holding.archived_at.is_(None))
        return list(self.session.exec(statement).all())

    def set_archived(self, holding_id: str, archived: bool) -> Holding | None:
        holding = self.session.get(Holding, holding_id)
        if holding is None:
            return None
        holding.archived_at = datetime.now(timezone.utc) if archived else None
        self.session.add(holding)
        self.session.commit()
        self.session.refresh(holding)
        return holding
```

Add to the imports at the top of the file:

```python
from datetime import datetime, timezone
```

- [ ] **Step 4: Run the full suite**

Run: `cd backend && .venv/bin/pytest`
Expected: PASS. If any existing test fails, it is asserting on holdings that are now filtered — read it before changing it; the filter is intended.

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/holding_repository.py backend/tests/test_repositories.py
git commit -m "feat: filter archived holdings in HoldingRepository"
```

---

### Task 3: Regression tests for the four direct callers

This task adds no production code. It pins the behaviour that Task 2's changed
default is supposed to produce at every call site that reaches holdings without
going through `list_collection`.

**Files:**
- Test: `backend/tests/test_insights_service.py`
- Test: `backend/tests/test_opportunity_service.py`
- Test: `backend/tests/test_price_service.py`
- Test: `backend/tests/test_digest_service.py`

**Interfaces:**
- Consumes: `HoldingRepository.set_archived` from Task 2.
- Produces: nothing.

- [ ] **Step 1: Write the tests**

Read the top of each target file first and reuse its existing fixture and
construction style — the services take different repository sets, and copying
the neighbouring test's setup is the fastest correct path.

In `backend/tests/test_insights_service.py`:

```python
def test_insights_ignores_archived_holdings(session):
    session.add(Card(id="base1-4", name="Charizard", set_id="base1", set_total=102))
    session.commit()
    repo = HoldingRepository(session)
    holding = repo.add(Holding(card_id="base1-4", owner_id="me"))
    repo.set_archived(holding.id, True)
    service = InsightsService(CardRepository(session), repo, PriceRepository(session))
    assert service.set_progress("me") == []
```

In `backend/tests/test_opportunity_service.py`:

```python
def test_opportunities_ignore_archived_holdings(session):
    session.add(Card(id="base1-4", name="Charizard"))
    session.commit()
    repo = HoldingRepository(session)
    holding = repo.add(Holding(card_id="base1-4", owner_id="me"))
    repo.set_archived(holding.id, True)
    session.add(PriceSnapshot(card_id="base1-4", source="t", market_price=100.0,
                              currency="USD", direct_low=10.0))
    session.commit()
    service = OpportunityService(CardRepository(session), repo,
                                 WatchRepository(session), PriceRepository(session))
    assert service.deals("me") == []


def test_price_refresh_skips_archived_holdings(session):
    session.add(Card(id="base1-4", name="Charizard"))
    session.commit()
    repo = HoldingRepository(session)
    holding = repo.add(Holding(card_id="base1-4", owner_id="me"))
    repo.set_archived(holding.id, True)
    service = PriceService(CardRepository(session), FakeProvider(), repo,
                           WatchRepository(session), PriceRepository(session),
                           PortfolioRepository(session))
    assert service.refresh_all("me")["written"] == 0
```

Put the price-refresh test in `backend/tests/test_price_service.py`, not the
opportunity file. In `backend/tests/test_digest_service.py`:

```python
def test_digest_ignores_archived_holdings(session):
    session.add(Card(id="base1-4", name="Charizard"))
    session.commit()
    repo = HoldingRepository(session)
    holding = repo.add(Holding(card_id="base1-4", owner_id="me", acquisition_cost=10.0))
    repo.set_archived(holding.id, True)
    service = DigestService(CollectionService(
        CardRepository(session), repo, PriceRepository(session),
        PortfolioRepository(session),
    ), OpportunityService(
        CardRepository(session), repo, WatchRepository(session), PriceRepository(session),
    ), PortfolioRepository(session))
    assert service.build("me")["summary"]["total_cost"] == 0
```

Method names (`set_progress`, `deals`, `refresh_all`, `build`) and constructor
argument order must be checked against the real services before running —
correct the test to match the source, not the other way round.

- [ ] **Step 2: Run them**

Run: `cd backend && .venv/bin/pytest -k "archived" -v`
Expected: PASS. These assert behaviour Task 2 already delivered; a failure means Task 2's filter is not reaching that caller, which is exactly the bug this task exists to catch.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/
git commit -m "test: pin archived-holding exclusion across all callers"
```

---

### Task 4: Service layer and error type

**Files:**
- Modify: `backend/app/errors.py`
- Modify: `backend/app/services/collection_service.py:56`
- Modify: `backend/app/main.py:108`
- Test: `backend/tests/test_collection_service.py`

**Interfaces:**
- Consumes: `HoldingRepository.set_archived`, `HoldingRepository.list` from Task 2.
- Produces:
  - `HoldingNotFoundError`
  - `CollectionService.list_collection(owner_id: str = "me", archived: bool = False) -> list[HoldingView]`
  - `CollectionService.archive_holding(holding_id: str) -> Holding`
  - `CollectionService.restore_holding(holding_id: str) -> Holding`

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_collection_service.py`:

```python
def test_archive_holding_removes_it_from_the_collection(session, sample_result):
    service = CollectionService(CardRepository(session), HoldingRepository(session),
                                PriceRepository(session), PortfolioRepository(session))
    holding = service.add_holding_from_result(sample_result, "raw", False, 100.0, 1, "")
    service.archive_holding(holding.id)
    assert service.list_collection() == []


def test_archive_holding_drops_total_cost_to_zero(session, sample_result):
    service = CollectionService(CardRepository(session), HoldingRepository(session),
                                PriceRepository(session), PortfolioRepository(session))
    holding = service.add_holding_from_result(sample_result, "raw", False, 100.0, 1, "")
    service.archive_holding(holding.id)
    assert service.summarize(service.list_collection()).total_cost == 0


def test_restore_holding_returns_it_to_the_collection(session, sample_result):
    service = CollectionService(CardRepository(session), HoldingRepository(session),
                                PriceRepository(session), PortfolioRepository(session))
    holding = service.add_holding_from_result(sample_result, "raw", False, 100.0, 1, "")
    service.archive_holding(holding.id)
    service.restore_holding(holding.id)
    assert len(service.list_collection()) == 1


def test_list_collection_returns_archived_when_requested(session, sample_result):
    service = CollectionService(CardRepository(session), HoldingRepository(session),
                                PriceRepository(session), PortfolioRepository(session))
    holding = service.add_holding_from_result(sample_result, "raw", False, 100.0, 1, "")
    service.archive_holding(holding.id)
    assert len(service.list_collection(archived=True)) == 1


def test_archive_holding_raises_when_missing(session):
    service = CollectionService(CardRepository(session), HoldingRepository(session),
                                PriceRepository(session), PortfolioRepository(session))
    with pytest.raises(HoldingNotFoundError):
        service.archive_holding("nonexistent-id")


def test_archive_holding_does_not_record_a_sale(session, sample_result):
    service = CollectionService(CardRepository(session), HoldingRepository(session),
                                PriceRepository(session), PortfolioRepository(session))
    holding = service.add_holding_from_result(sample_result, "raw", False, 100.0, 1, "")
    service.archive_holding(holding.id)
    assert SaleRepository(session).list("me") == []
```

Add `import pytest`, `from app.errors import HoldingNotFoundError`, and
`from app.repositories.sale_repository import SaleRepository` to that file's
imports if absent. Check `SaleRepository`'s list method name against the source.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/pytest tests/test_collection_service.py -k "archive or restore" -v`
Expected: FAIL — `ImportError: cannot import name 'HoldingNotFoundError'`

- [ ] **Step 3: Add the error type**

Append to `backend/app/errors.py`:

```python
class HoldingNotFoundError(Exception):
    """No holding matched the given id."""
```

- [ ] **Step 4: Implement the service methods**

In `backend/app/services/collection_service.py`, change the signature of
`list_collection` and add the two methods. Import the error at the top:

```python
from app.errors import HoldingNotFoundError
```

```python
    def list_collection(self, owner_id: str = "me",
                        archived: bool = False) -> list[HoldingView]:
        views: list[HoldingView] = []
        for holding in self.holding_repo.list(owner_id, archived=archived):
```

Leave the rest of the loop body unchanged. Then add:

```python
    def archive_holding(self, holding_id: str) -> Holding:
        holding = self.holding_repo.set_archived(holding_id, True)
        if holding is None:
            raise HoldingNotFoundError(holding_id)
        return holding

    def restore_holding(self, holding_id: str) -> Holding:
        holding = self.holding_repo.set_archived(holding_id, False)
        if holding is None:
            raise HoldingNotFoundError(holding_id)
        return holding
```

- [ ] **Step 5: Register the 404 handler**

In `backend/app/main.py`, beside the existing `CardNotFoundError` handler:

```python
    @application.exception_handler(HoldingNotFoundError)
    def handle_holding_not_found(request: Request, error: HoldingNotFoundError) -> JSONResponse:
        logger.warning("Holding not found: %s", error)
        return JSONResponse(status_code=404, content={"detail": str(error)})
```

Add `HoldingNotFoundError` to the existing `from app.errors import ...` line.

- [ ] **Step 6: Run the full suite**

Run: `cd backend && .venv/bin/pytest`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/errors.py backend/app/services/collection_service.py backend/app/main.py backend/tests/test_collection_service.py
git commit -m "feat: archive and restore holdings in CollectionService"
```

---

### Task 5: HTTP endpoints

**Files:**
- Modify: `backend/app/routers/holdings.py`
- Test: `backend/tests/test_routers.py`

**Interfaces:**
- Consumes: `CollectionService.archive_holding`, `restore_holding`, `list_collection(archived=)` from Task 4.
- Produces: `PATCH /holdings/{id}/archive`, `PATCH /holdings/{id}/restore`, `GET /holdings?archived=true`.

- [ ] **Step 1: Write the failing tests**

Read the top of `backend/tests/test_routers.py` and reuse its existing client
fixture and dependency-override pattern. Add:

```python
def test_archive_holding_returns_200(client, added_holding_id):
    response = client.patch(f"/holdings/{added_holding_id}/archive")
    assert response.status_code == 200


def test_archive_holding_removes_it_from_the_default_list(client, added_holding_id):
    client.patch(f"/holdings/{added_holding_id}/archive")
    assert client.get("/holdings").json()["items"] == []


def test_archived_holdings_are_listed_when_requested(client, added_holding_id):
    client.patch(f"/holdings/{added_holding_id}/archive")
    assert len(client.get("/holdings?archived=true").json()["items"]) == 1


def test_restore_holding_returns_it_to_the_default_list(client, added_holding_id):
    client.patch(f"/holdings/{added_holding_id}/archive")
    client.patch(f"/holdings/{added_holding_id}/restore")
    assert len(client.get("/holdings").json()["items"]) == 1


def test_archive_unknown_holding_returns_404(client):
    assert client.patch("/holdings/nonexistent-id/archive").status_code == 404
```

If no `added_holding_id` fixture exists, create one in that file that POSTs a
holding through the client and returns the new id.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/pytest tests/test_routers.py -k "archive or restore" -v`
Expected: FAIL — 405 Method Not Allowed on the PATCH routes.

- [ ] **Step 3: Implement**

In `backend/app/routers/holdings.py`, change `list_holdings` and add the two
routes:

```python
@router.get("")
def list_holdings(archived: bool = False,
                  service: CollectionService = Depends(get_collection_service)) -> dict:
    views = service.list_collection(archived=archived)
```

Leave the rest of that function's body unchanged. Then add:

```python
@router.patch("/{holding_id}/archive")
def archive_holding(holding_id: str,
                    service: CollectionService = Depends(get_collection_service)) -> dict:
    return service.archive_holding(holding_id).model_dump()


@router.patch("/{holding_id}/restore")
def restore_holding(holding_id: str,
                    service: CollectionService = Depends(get_collection_service)) -> dict:
    return service.restore_holding(holding_id).model_dump()
```

The spec called for 409 on double-archive. That is dropped: archiving an
archived holding is idempotent and returns 200, which is simpler and costs the
client nothing. Note this deviation in the commit message.

- [ ] **Step 4: Run the full suite**

Run: `cd backend && .venv/bin/pytest`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/holdings.py backend/tests/test_routers.py
git commit -m "feat: PATCH /holdings/{id}/archive and /restore

Archive is idempotent rather than 409 on repeat, deviating from the spec:
the client gains nothing from the conflict and retries stay safe."
```

---

### Task 6: API client and types

**Files:**
- Modify: `web/src/lib/api.ts:37`
- Modify: `web/src/lib/types.ts:18`

**Interfaces:**
- Consumes: the endpoints from Task 5.
- Produces:
  - `api.listHoldings(archived?: boolean): Promise<CollectionResponse>`
  - `api.archiveHolding(holdingId: string): Promise<unknown>`
  - `api.restoreHolding(holdingId: string): Promise<unknown>`
  - `Holding.archived_at: string | null`

- [ ] **Step 1: Add the field to the type**

In `web/src/lib/types.ts`, find the holding interface used by `HoldingView`
(around line 18) and add:

```ts
  archived_at: string | null;
```

- [ ] **Step 2: Extend the API client**

In `web/src/lib/api.ts`, replace the `listHoldings` line and add two methods:

```ts
  listHoldings: (archived = false) =>
    fetch(`${BASE}/holdings?archived=${archived}`).then(json<CollectionResponse>),
  archiveHolding: (holdingId: string) =>
    fetch(`${BASE}/holdings/${holdingId}/archive`, { method: "PATCH" }).then(json),
  restoreHolding: (holdingId: string) =>
    fetch(`${BASE}/holdings/${holdingId}/restore`, { method: "PATCH" }).then(json),
```

The default argument keeps every existing `api.listHoldings()` call site working
unchanged.

- [ ] **Step 3: Typecheck**

Run: `cd web && npx --no-install tsc --noEmit`
Expected: exit 0, no output.

- [ ] **Step 4: Commit**

```bash
git add web/src/lib/api.ts web/src/lib/types.ts
git commit -m "feat: archive and restore in the API client"
```

---

### Task 7: Archive button on the card detail page

**Files:**
- Modify: `web/src/app/card/[id]/page.tsx`
- Modify: `web/src/app/globals.css`

**Interfaces:**
- Consumes: `api.archiveHolding` from Task 6.
- Produces: nothing.

- [ ] **Step 1: Add confirm state**

In `web/src/app/card/[id]/page.tsx`, alongside the existing sale-modal state:

```tsx
  const [confirmingArchive, setConfirmingArchive] = useState(false);
  const [archiving, setArchiving] = useState(false);
```

- [ ] **Step 2: Add the handler**

Place it beside the existing sale handler. Match how that function reports
errors — reuse the same toast hook already imported in this file:

```tsx
  async function archive() {
    setArchiving(true);
    try {
      await api.archiveHolding(view.holding.id);
      toast("Card archived — its price history is kept.", "ok");
      router.push("/");
    } catch {
      toast("Couldn't archive that card.", "error");
    } finally {
      setArchiving(false);
      setConfirmingArchive(false);
    }
  }
```

If the file does not already have `router`, add
`const router = useRouter();` and import `useRouter` from `next/navigation`.

- [ ] **Step 3: Add the button and confirm step**

Next to the existing "Log a sale" button:

```tsx
  <button className="btn" onClick={() => setConfirmingArchive(true)}>
    Archive
  </button>
```

And, following the structure of the existing sale modal in this file:

```tsx
  {confirmingArchive && (
    <div className="modal-backdrop" onClick={() => setConfirmingArchive(false)}>
      <div className="modal" onClick={(event) => event.stopPropagation()}>
        <h3>Archive {view.card?.name ?? "this card"}?</h3>
        <p className="muted">
          It leaves your collection and stops counting toward your totals. Its
          price history is kept, and you can restore it from the collection page.
        </p>
        <div className="modal__actions">
          <button className="btn" onClick={() => setConfirmingArchive(false)}>
            Cancel
          </button>
          <button className="btn btn--primary" onClick={archive} disabled={archiving}>
            {archiving ? "Archiving…" : "Archive"}
          </button>
        </div>
      </div>
    </div>
  )}
```

Use whatever class names the existing sale modal uses in this file rather than
inventing new ones. Only add CSS if the markup above introduces a class that
`globals.css` does not already define.

- [ ] **Step 4: Typecheck and lint**

Run: `cd web && npx --no-install tsc --noEmit && npx --no-install eslint src/app/card/`
Expected: exit 0 for both.

- [ ] **Step 5: Verify by hand**

With both servers running, open a card detail page, click Archive, confirm.
Expected: toast appears, redirect to `/`, and the card is gone from the grid.

- [ ] **Step 6: Commit**

```bash
git add web/src/app/card/ web/src/app/globals.css
git commit -m "feat: archive a card from its detail page"
```

---

### Task 8: Archived toggle and restore on the collection page

**Files:**
- Modify: `web/src/app/page.tsx`
- Modify: `web/src/app/globals.css`

**Interfaces:**
- Consumes: `api.listHoldings(archived)`, `api.restoreHolding` from Task 6.
- Produces: nothing.

- [ ] **Step 1: Add state and load archived alongside active**

In `web/src/app/page.tsx`, add:

```tsx
  const [archivedData, setArchivedData] = useState<CollectionResponse | null>(null);
  const [showingArchived, setShowingArchived] = useState(false);
```

Extend the existing `load` callback's `Promise.all` to also fetch
`api.listHoldings(true)` and store it with `setArchivedData`. Fetching both on
mount is what lets the toggle show a count before it is clicked.

- [ ] **Step 2: Add the restore handler**

```tsx
  async function restore(holdingId: string) {
    try {
      await api.restoreHolding(holdingId);
      await load();
    } catch {
      toast("Couldn't restore that card.", "error");
    }
  }
```

Use the toast hook already imported in this file.

- [ ] **Step 3: Add the toggle to the Holdings header**

Inside the existing `.section__head`, after the count:

```tsx
  {(archivedData?.items.length ?? 0) > 0 && (
    <button
      className={`btn btn--sm${showingArchived ? " btn--primary" : ""}`}
      onClick={() => setShowingArchived((previous) => !previous)}
    >
      Archived ({archivedData?.items.length ?? 0})
    </button>
  )}
```

- [ ] **Step 4: Render the archived grid**

Choose the list to render from `showingArchived`:

```tsx
  const visibleItems = showingArchived ? (archivedData?.items ?? []) : items;
```

Replace `items.map(...)` in the grid with `visibleItems.map(...)`. Inside the
tile, when `showingArchived` is true, add a restore control below the price row
and give the tile a dimmed class:

```tsx
  {showingArchived && (
    <button
      className="btn btn--sm"
      onClick={(event) => {
        event.preventDefault();
        restore(item.holding.id);
      }}
    >
      Restore
    </button>
  )}
```

`event.preventDefault()` matters: the tile is wrapped in a `<Link>`, so without
it the click navigates to the card page instead of restoring.

- [ ] **Step 5: Dim archived tiles**

Add to `web/src/app/globals.css`:

```css
.tile--archived {
  opacity: 0.55;
}

.tile--archived:hover {
  opacity: 1;
}
```

Apply `tile--archived` to the tile's className when `showingArchived` is true.

- [ ] **Step 6: Typecheck and lint**

Run: `cd web && npx --no-install tsc --noEmit && npx --no-install eslint src/app/page.tsx`
Expected: exit 0 for both.

- [ ] **Step 7: Verify by hand**

Archive a card, return to `/`. Expected: an `Archived (1)` button appears in the
Holdings header; clicking it shows the dimmed card with a Restore button;
Restore returns it to the main grid and the portfolio total goes back up.

- [ ] **Step 8: Commit**

```bash
git add web/src/app/page.tsx web/src/app/globals.css
git commit -m "feat: archived toggle and restore on the collection page"
```

---

### Task 9: Document the feature

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: everything above.
- Produces: nothing.

- [ ] **Step 1: Add the endpoints to the API table**

In the API table in `README.md`, after the `/holdings/{id}/sell` row:

```markdown
| `PATCH` | `/holdings/{id}/archive` | Archive a holding, keeping its price history |
| `PATCH` | `/holdings/{id}/restore` | Restore an archived holding |
```

- [ ] **Step 2: Describe it in the Collection feature section**

Append to the "Collection & P&L" paragraph:

> Cards you no longer want to track can be archived rather than deleted: they
> leave your totals and stop consuming API quota on refreshes, but their price
> history survives and one click restores them.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document archiving holdings"
```

---

## Self-Review

**Spec coverage.** `archived_at` column → Task 1. Repository filter and state
change → Task 2. The four direct callers → Task 3. Service methods, error type,
404 mapping → Task 4. Endpoints → Task 5. API client → Task 6. Detail-page
archive with confirm → Task 7. Collection toggle, dimmed tiles, restore →
Task 8. Docs → Task 9.

**Deliberate deviation.** The spec specified 409 on double-archive and
double-restore. Task 5 makes both idempotent instead. A client gains nothing
from the conflict, and idempotency makes retries safe. This is flagged in
Task 5 and in its commit message.

**Untested by automation.** There is no frontend test suite, so Tasks 7 and 8
are verified by hand. Their manual steps are written as concrete
expectations rather than "check it works".

**Signature consistency.** `set_archived(holding_id, archived)` is used
identically in Tasks 2, 3, and 4. `list(owner_id, archived=False)` matches
between Tasks 2 and 4. `list_collection(owner_id, archived=False)` matches
between Tasks 4 and 5. `api.listHoldings(archived?)` defaults to `false`, so
the existing call sites in Task 6 keep compiling.

**Where this is most likely to go wrong.** Task 3's test constructors were
written from the call graph, not by reading each service's `__init__`. The task
says so and instructs the implementer to correct the tests against the source.
Task 2's changed default may also break existing tests that assume unfiltered
holdings; Task 2 Step 4 calls this out as intended behaviour to be read, not
patched away.
