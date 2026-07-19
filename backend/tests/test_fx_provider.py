import httpx
import respx

from app.errors import PriceProviderError
from app.providers.fx_provider import BASE_URL, FxProvider


@respx.mock
def test_get_usd_brl_maps_rate():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, json={"rates": {"BRL": 5.4}}))
    provider = FxProvider(client=httpx.Client())
    assert provider.get_usd_brl() == 5.4


@respx.mock
def test_get_usd_brl_transport_error_raises_price_provider_error():
    respx.get(BASE_URL).mock(side_effect=httpx.ConnectError("boom"))
    provider = FxProvider(client=httpx.Client())
    try:
        provider.get_usd_brl()
        raised = False
    except PriceProviderError:
        raised = True
    assert raised


@respx.mock
def test_get_usd_brl_missing_brl_key_raises_price_provider_error():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, json={"rates": {}}))
    provider = FxProvider(client=httpx.Client())
    try:
        provider.get_usd_brl()
        raised = False
    except PriceProviderError:
        raised = True
    assert raised
