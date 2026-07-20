from app.models import Card, Holding, PriceSnapshot
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository
from app.services.insights_service import InsightsService


def _service(session) -> InsightsService:
    return InsightsService(CardRepository(session), HoldingRepository(session), PriceRepository(session))


def _seed_two_sets(session) -> None:
    card_repo = CardRepository(session)
    holding_repo = HoldingRepository(session)
    price_repo = PriceRepository(session)

    card_repo.upsert(Card(
        id="base1-4", name="Charizard", set_id="base1", set_name="Base",
        set_total=102, rarity="Rare Holo",
    ))
    card_repo.upsert(Card(
        id="base1-2", name="Blastoise", set_id="base1", set_name="Base",
        set_total=102, rarity="Rare",
    ))
    card_repo.upsert(Card(
        id="jungle-5", name="Pikachu", set_id="jungle", set_name="Jungle",
        set_total=64, rarity="Common",
    ))

    holding_repo.add(Holding(card_id="base1-4", owner_id="me", quantity=1))
    holding_repo.add(Holding(card_id="base1-2", owner_id="me", quantity=2))
    holding_repo.add(Holding(card_id="jungle-5", owner_id="me", quantity=1))

    price_repo.add(PriceSnapshot(card_id="base1-4", market_price=100.0))
    price_repo.add(PriceSnapshot(card_id="base1-2", market_price=50.0))
    price_repo.add(PriceSnapshot(card_id="jungle-5", market_price=20.0))


def _find_set(rows: list[dict], set_id: str) -> dict:
    return next(row for row in rows if row["set_id"] == set_id)


def test_set_progress_owned_counts_distinct_cards_in_set(session):
    _seed_two_sets(session)
    rows = _service(session).set_progress()
    assert _find_set(rows, "base1")["owned"] == 2


def test_set_progress_total_matches_set_total(session):
    _seed_two_sets(session)
    rows = _service(session).set_progress()
    assert _find_set(rows, "base1")["total"] == 102


def test_set_progress_pct_matches_owned_over_total(session):
    _seed_two_sets(session)
    rows = _service(session).set_progress()
    assert _find_set(rows, "base1")["pct"] == (2 / 102 * 100.0)


def test_set_progress_is_sorted_by_pct_descending(session):
    _seed_two_sets(session)
    rows = _service(session).set_progress()
    assert [row["set_id"] for row in rows] == ["base1", "jungle"]


def test_allocation_total_value_sums_holding_values(session):
    _seed_two_sets(session)
    allocation = _service(session).allocation()
    assert allocation["total_value"] == 220.0


def test_allocation_by_set_values_sum_to_total_value(session):
    _seed_two_sets(session)
    allocation = _service(session).allocation()
    assert sum(row["value"] for row in allocation["by_set"]) == allocation["total_value"]


def test_allocation_by_rarity_values_sum_to_total_value(session):
    _seed_two_sets(session)
    allocation = _service(session).allocation()
    assert sum(row["value"] for row in allocation["by_rarity"]) == allocation["total_value"]


def test_allocation_top_cards_is_sorted_descending(session):
    _seed_two_sets(session)
    allocation = _service(session).allocation()
    values = [row["value"] for row in allocation["top_cards"]]
    assert values == sorted(values, reverse=True)


def test_build_with_empty_collection_returns_no_sets(session):
    result = _service(session).build()
    assert result["sets"] == []


def test_build_with_empty_collection_returns_zero_total_value(session):
    result = _service(session).build()
    assert result["allocation"]["total_value"] == 0.0


def test_build_with_empty_collection_returns_no_top_cards(session):
    result = _service(session).build()
    assert result["allocation"]["top_cards"] == []


def test_set_progress_ignores_archived_holdings(session):
    card_repo = CardRepository(session)
    holding_repo = HoldingRepository(session)
    card_repo.upsert(Card(
        id="base1-4", name="Charizard", set_id="base1", set_name="Base", set_total=102,
    ))
    holding = holding_repo.add(Holding(card_id="base1-4", owner_id="me"))
    holding_repo.set_archived(holding.id, True)

    rows = _service(session).set_progress()

    assert rows == []


def test_allocation_ignores_archived_holdings(session):
    card_repo = CardRepository(session)
    holding_repo = HoldingRepository(session)
    price_repo = PriceRepository(session)
    card_repo.upsert(Card(id="base1-4", name="Charizard"))
    holding = holding_repo.add(Holding(card_id="base1-4", owner_id="me"))
    holding_repo.set_archived(holding.id, True)
    price_repo.add(PriceSnapshot(card_id="base1-4", market_price=100.0))

    allocation = _service(session).allocation()

    assert allocation["total_value"] == 0.0
