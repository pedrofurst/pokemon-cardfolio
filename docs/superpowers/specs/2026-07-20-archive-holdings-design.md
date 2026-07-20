# Archive holdings — design

**Date:** 2026-07-20
**Status:** approved, ready for implementation planning

## Problem

There is no way to remove a card from the collection. The only path that removes
a holding is `POST /holdings/{id}/sell`, which also writes a `Sale` row and moves
realized P&L. A user who mistypes a card, adds a duplicate, or simply stops
tracking something has to edit SQLite by hand.

## Decision

Add **archiving**, not deletion. An archived holding disappears from the
collection and stops affecting any number in the app, but its row and its price
history survive and it can be restored.

Deletion was rejected because price history is the app's most expensive asset —
it accrues only through repeated refreshes over time and cannot be backfilled
from the provider. A destructive remove would silently discard it.

Archiving is deliberately **not** a sale. Sales are the only source of realized
P&L, and that stays true: archiving never writes a `Sale` row and never moves a
realized number.

## Semantics

| Question | Answer |
| --- | --- |
| Granularity | Whole holding, all quantities. Partial disposal is what the sell flow is for. |
| Portfolio totals | Excluded — value, cost basis, unrealized P&L, and card count all ignore archived holdings. |
| Insights & digest | Excluded, since both derive from the collection list. |
| Price refresh | Skipped, so archived cards stop consuming API quota. |
| Existing price history | Retained untouched. |
| Realized P&L | Unaffected. |
| Restore | Returns the holding to the collection exactly as it was. |

## Data model

One column on `Holding`:

```python
archived_at: datetime | None = None
```

`None` means active. A timestamp rather than a boolean costs nothing and lets the
UI order by most-recently-archived.

The column is added through the existing `_MIGRATION_COLUMNS` list in
`app/db.py`, which is the established pattern for `holding.variant`,
`card.set_id`, and the `pricesnapshot` price columns. No Alembic.

## API

| Method | Path | Behaviour |
| --- | --- | --- |
| `PATCH` | `/holdings/{id}/archive` | Sets `archived_at`. Returns the updated holding. 404 if unknown, 409 if already archived. |
| `PATCH` | `/holdings/{id}/restore` | Clears `archived_at`. Returns the updated holding. 404 if unknown, 409 if not archived. |
| `GET` | `/holdings?archived=true` | Lists archived holdings. Defaults to `false`. |

`PATCH` rather than `DELETE`: the resource is not being removed, and both
directions are the same kind of state change on the same field.

The existing `GET /holdings` response shape is unchanged.

## Backend changes

The filter belongs in **`HoldingRepository.list`**, not in `CollectionService`.
The call graph is wider than it first appears — five call sites reach holdings,
and only one of them goes through `list_collection`:

| Caller | Path |
| --- | --- |
| `collection_service.list_collection` | `holding_repo.list` |
| `insights_service` (two sites) | `holding_repo.list` directly |
| `opportunity_service` | `holding_repo.list` directly |
| `price_service.refresh` | `holding_repo.list` directly |
| `digest_service` | via `collection_service.list_collection` |

Filtering in `list_collection` would therefore miss insights, opportunities, and
price refresh, leaving archived cards silently counted in set completion and
allocation and still consuming API quota on every refresh. Defaulting the
repository to active-only fixes all five at once.

- `HoldingRepository.list(owner_id, archived: bool = False)` filters on
  `archived_at IS NULL` / `IS NOT NULL`.
- `HoldingRepository.set_archived(holding_id, archived: bool)` performs the
  state change and returns the updated holding, or `None` if not found.
- `CollectionService.list_collection(owner_id, archived=False)` passes the flag
  through so the UI can request the archived grid.
- `CollectionService.archive_holding` / `restore_holding` wrap the repository
  calls and raise `HoldingNotFoundError` (new, in `app/errors.py`, mapped to 404
  alongside the existing `CardNotFoundError` handler).

Changing a shared repository default is the riskiest part of this design: it
alters behaviour for four callers that never mention archiving. That is the
intent, but it means each of those callers needs its own regression test rather
than relying on the repository test alone.

## Frontend changes

- **Card detail page** — an `Archive` button beside `Log a sale`, behind a
  confirm step that names the card and states that history is kept and the card
  can be restored. On success: toast, redirect to `/`.
- **Collection page** — the Holdings section header gains an
  `Archived (n)` toggle that swaps the grid to archived holdings. Each archived
  tile renders dimmed with a `Restore` button. The count comes from the archived
  list, fetched once on mount so the toggle can be labelled without a click.
- No new route and no eleventh sidebar entry: archived cards stay where the user
  archived them from.
- `api.ts` gains `archiveHolding`, `restoreHolding`, and an `archived` parameter
  on `listHoldings`.

## Testing

Backend, following the existing one-assertion-per-test convention:

- Repository: archived rows excluded from the default list, included when asked;
  `set_archived` round-trips both directions; unknown id returns `None`.
- Service: archiving removes a holding from `list_collection`; totals drop by
  exactly that holding's value and cost; restore reverses it; archiving does not
  create a `Sale`; realized P&L is unchanged by an archive.
- Regression coverage for each caller of the changed repository default, one
  test apiece: digest, insights (set completion and allocation), opportunities,
  and price refresh all ignore archived holdings. Price refresh in particular
  must not request a price for an archived card.
- Router: 200 on archive and restore, 404 on unknown id, 409 on double-archive,
  and `GET /holdings?archived=true` returns only archived rows.
- Migration: the column is added to a database created before it existed, and
  running migrations twice is a no-op.

There is no frontend test suite, so the UI is verified by hand.

## Out of scope

Bulk archive, an archive reason or note, auto-archiving on zero quantity, and
permanent deletion of archived holdings.
