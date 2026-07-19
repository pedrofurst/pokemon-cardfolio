import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db import init_db
from app.errors import CardNotFoundError, PriceProviderError
from app.routers import (
    cards,
    digest,
    grading,
    history,
    holdings,
    opportunities,
    price_check,
    prices,
    sales,
    watchlist,
)

logger = logging.getLogger(__name__)

# Accept the web app on any localhost port (Next may fall back to 3001, etc.).
ALLOWED_ORIGIN_REGEX = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    init_db()
    scheduler_enabled = get_settings().enable_scheduler
    if scheduler_enabled:
        # Imported here (rather than at module load) to avoid a potential
        # import cycle between app.main and app.scheduler / app.deps.
        from app.scheduler import start_scheduler

        start_scheduler()
    yield
    if scheduler_enabled:
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

    @application.exception_handler(CardNotFoundError)
    def handle_card_not_found(request: Request, error: CardNotFoundError) -> JSONResponse:
        logger.warning("Card not found: %s", error)
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
