import time

from fastapi import APIRouter, Depends

from app.deps import get_fx_provider
from app.providers.fx_provider import FxProvider

router = APIRouter(tags=["fx"])

_CACHE_TTL_SECONDS = 3600.0

# Module-level in-process cache: avoids hammering the external FX API on
# every request. Keyed by nothing (single rate) since we only ever fetch
# USD->BRL. `expires_at` is a time.monotonic() timestamp.
_cache: dict = {"usd_brl": None, "expires_at": 0.0}


def clear_fx_cache() -> None:
    """Reset the module-level cache. Used by tests to avoid cross-test leakage."""
    _cache["usd_brl"] = None
    _cache["expires_at"] = 0.0


@router.get("/fx")
def get_fx(provider: FxProvider = Depends(get_fx_provider)) -> dict:
    now = time.monotonic()
    if _cache["usd_brl"] is None or now >= _cache["expires_at"]:
        usd_brl = provider.get_usd_brl()
        _cache["usd_brl"] = usd_brl
        _cache["expires_at"] = now + _CACHE_TTL_SECONDS
    return {"usd_brl": _cache["usd_brl"]}
