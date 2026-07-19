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
    assert result.id == "base1-4"
    assert result.name == "Charizard"
    assert result.set_name == "Base"
    assert result.number == "4"
    assert result.rarity == "Rare Holo"
    assert result.image_url == "https://img/charizard.png"
    assert result.market_price == 350.0


@respx.mock
def test_search_cards_malformed_json_raises_price_provider_error():
    respx.get(f"{BASE}/cards").mock(return_value=httpx.Response(200, text="not json"))
    provider = PokemonTcgIoProvider(api_key="k", client=httpx.Client())
    try:
        provider.search_cards("charizard")
        raised = False
    except PriceProviderError:
        raised = True
    assert raised


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
def test_get_price_missing_market_price_raises_price_provider_error():
    card_without_price = {**CARD_JSON, "tcgplayer": {"prices": {}}}
    respx.get(f"{BASE}/cards/base1-4").mock(
        return_value=httpx.Response(200, json={"data": card_without_price})
    )
    provider = PokemonTcgIoProvider(api_key="k", client=httpx.Client())
    try:
        provider.get_price("base1-4")
        raised = False
    except PriceProviderError:
        raised = True
    assert raised


@respx.mock
def test_get_price_maps_full_tcgplayer_price_detail():
    card_with_full_prices = {
        **CARD_JSON,
        "tcgplayer": {
            "prices": {
                "holofoil": {"low": 1, "mid": 2, "high": 3, "market": 10, "directLow": 7}
            }
        },
    }
    respx.get(f"{BASE}/cards/base1-4").mock(
        return_value=httpx.Response(200, json={"data": card_with_full_prices})
    )
    provider = PokemonTcgIoProvider(api_key="k", client=httpx.Client())
    result = provider.get_price("base1-4")
    assert result.market_price == 10.0
    assert result.direct_low == 7.0


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


SET_JSON = {
    "id": "base1",
    "name": "Base",
    "series": "Base",
    "total": 102,
    "releaseDate": "1999/01/09",
    "images": {"symbol": "https://img/base-symbol.png", "logo": "https://img/base-logo.png"},
}


@respx.mock
def test_list_sets_maps_fields():
    respx.get(f"{BASE}/sets").mock(return_value=httpx.Response(200, json={"data": [SET_JSON]}))
    provider = PokemonTcgIoProvider(api_key="k", client=httpx.Client())
    result = provider.list_sets(limit=12)[0]
    assert result.id == "base1"
    assert result.name == "Base"
    assert result.series == "Base"
    assert result.total == 102
    assert result.release_date == "1999/01/09"
    assert result.logo_url == "https://img/base-logo.png"


@respx.mock
def test_list_sets_wraps_transport_error():
    respx.get(f"{BASE}/sets").mock(side_effect=httpx.ConnectError("boom"))
    provider = PokemonTcgIoProvider(api_key="k", client=httpx.Client())
    try:
        provider.list_sets()
        raised = False
    except PriceProviderError:
        raised = True
    assert raised


@respx.mock
def test_list_sets_malformed_json_raises_price_provider_error():
    respx.get(f"{BASE}/sets").mock(return_value=httpx.Response(200, text="not json"))
    provider = PokemonTcgIoProvider(api_key="k", client=httpx.Client())
    try:
        provider.list_sets()
        raised = False
    except PriceProviderError:
        raised = True
    assert raised


@respx.mock
def test_get_set_cards_returns_mapped_card_results():
    respx.get(f"{BASE}/cards").mock(return_value=httpx.Response(200, json={"data": [CARD_JSON]}))
    provider = PokemonTcgIoProvider(api_key="k", client=httpx.Client())
    result = provider.get_set_cards("base1")[0]
    assert result.id == "base1-4"


@respx.mock
def test_get_set_cards_wraps_transport_error():
    respx.get(f"{BASE}/cards").mock(side_effect=httpx.ConnectError("boom"))
    provider = PokemonTcgIoProvider(api_key="k", client=httpx.Client())
    try:
        provider.get_set_cards("base1")
        raised = False
    except PriceProviderError:
        raised = True
    assert raised
