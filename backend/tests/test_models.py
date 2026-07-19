from app.models import Card, Holding


def test_holding_defaults_owner_to_me(session):
    session.add(Card(id="base1-4", name="Charizard"))
    holding = Holding(card_id="base1-4", acquisition_cost=120.0)
    session.add(holding)
    session.commit()
    session.refresh(holding)
    assert holding.owner_id == "me"
