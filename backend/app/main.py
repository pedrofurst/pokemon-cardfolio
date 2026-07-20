import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db import init_db
from app.errors import CardNotFoundError, HoldingNotFoundError, PriceProviderError
from app.routers import (
    cards,
    digest,
    fx,
    grading,
    history,
    holdings,
    insights,
    opportunities,
    price_check,
    prices,
    sales,
    store,
    watchlist,
)

logger = logging.getLogger(__name__)

# Accept the web app on any localhost port (Next may fall back to 3001, etc.).
ALLOWED_ORIGIN_REGEX = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"


def _warm_store_cache() -> None:
    """Best-effort store cache warm-up, run on a background thread.

    Builds its own provider/service instances so it never touches request-
    scoped dependencies. Any failure (network, rate limit, etc.) is
    swallowed — the store simply falls back to a cold/slow build on the
    first real request, same as before this warm-up existed.
    """
    try:
        from app.providers.pokemontcgio import PokemonTcgIoProvider
        from app.services.store_service import StoreService

        settings = get_settings()
        provider = PokemonTcgIoProvider(api_key=settings.pokemontcg_api_key)
        StoreService(provider).build()
    except Exception:
        logger.warning("Store cache warm-up failed", exc_info=True)


def _start_store_warm_thread_if_needed() -> None:
    # Imported here (rather than at module load) to avoid a potential
    # import cycle between app.main and app.services.store_service.
    from app.services.store_service import has_fresh_cache

    if has_fresh_cache():
        return
    thread = threading.Thread(target=_warm_store_cache, daemon=True)
    thread.start()


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    init_db()
    settings = get_settings()
    if settings.enable_scheduler:
        # Imported here (rather than at module load) to avoid a potential
        # import cycle between app.main and app.scheduler / app.deps.
        from app.scheduler import start_scheduler

        start_scheduler()
    if settings.warm_store_on_startup:
        _start_store_warm_thread_if_needed()
    yield
    if settings.enable_scheduler:
        from app.scheduler import shutdown_scheduler

        shutdown_scheduler()


def create_application() -> FastAPI:
    application = FastAPI(title="Cardfolio API", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origin_regex=ALLOWED_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(cards.router)
    application.include_router(holdings.router)
    application.include_router(prices.router)
    application.include_router(watchlist.router)
    application.include_router(opportunities.router)
    application.include_router(grading.router)
    application.include_router(history.router)
    application.include_router(price_check.router)
    application.include_router(sales.router)
    application.include_router(digest.router)
    application.include_router(insights.router)
    application.include_router(fx.router)
    application.include_router(store.router)

    @application.exception_handler(CardNotFoundError)
    def handle_card_not_found(request: Request, error: CardNotFoundError) -> JSONResponse:
        logger.warning("Card not found: %s", error)
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @application.exception_handler(HoldingNotFoundError)
    def handle_holding_not_found(request: Request, error: HoldingNotFoundError) -> JSONResponse:
        logger.warning("Holding not found: %s", error)
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @application.exception_handler(PriceProviderError)
    def handle_price_provider_error(request: Request, error: PriceProviderError) -> JSONResponse:
        logger.error("Price provider failed: %s", error)
        return JSONResponse(status_code=502, content={"detail": str(error)})

    @application.get("/health")
    def get_health() -> dict:
        return {"status": "ok"}

    return application


app = create_application()
