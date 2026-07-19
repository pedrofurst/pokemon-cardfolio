import httpx
import respx

from app.errors import CardNotFoundError, PriceProviderError
from app.providers.pokemontcgio import PokemonTcgIoProvider

BASE = "https://api.pokemontcg.io/v2"

CARD_JSON = {
    "id": "base1-4",
    "name": "Charizard",
    "number": "4",
    "rarity": "Rare Holo",
    "set": {"name": "Base"},
    "images": {"small": "https://img/charizard.png"},
    "tcgplayer": {"prices": {"holofoil": {"market": 350.0}}},
}


@respx.mock
def test_search_cards_maps_fields():
    respx.get(f"{BASE}/cards").mock(
        return_value=httpx.Response(200, json={"data": [CARD_JSON]})
    )
    provider = PokemonTcgIoProvider(api_key="k", client=httpx.Client())
    result = provider.search_cards("charizard")[0]
    assert result.market_price == 350.0


@respx.mock
def test_get_price_missing_card_raises_not_found():
    respx.get(f"{BASE}/cards/nope").mock(return_value=httpx.Response(404))
    provider = PokemonTcgIoProvider(api_key="k", client=httpx.Client())
    try:
        provider.get_price("nope")
        raised = False
    except CardNotFoundError:
        raised = True
    assert raised


@respx.mock
def test_provider_wraps_transport_error():
    respx.get(f"{BASE}/cards").mock(side_effect=httpx.ConnectError("boom"))
    provider = PokemonTcgIoProvider(api_key="k", client=httpx.Client())
    try:
        provider.search_cards("x")
        raised = False
    except PriceProviderError:
        raised = True
    assert raised
