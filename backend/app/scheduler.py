import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlmodel import Session

from app.config import get_settings
from app.db import get_engine
from app.deps import _provider
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.price_repository import PriceRepository
from app.repositories.watch_repository import WatchRepository
from app.services.collection_service import CollectionService
from app.services.price_service import PriceService

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _run_daily_refresh() -> None:
    # The scheduled job must never crash the scheduler thread: isolate any
    # failure here (bad session, provider outage, ...) and log it instead.
    try:
        with Session(get_engine()) as session:
            price_service = PriceService(
                CardRepository(session), PriceRepository(session),
                _provider, HoldingRepository(session), WatchRepository(session),
            )
            collection_service = CollectionService(
                CardRepository(session), HoldingRepository(session),
                PriceRepository(session), PortfolioRepository(session),
            )
            price_service.refresh_prices("me")
            collection_service.record_portfolio_snapshot("me")
    except Exception:
        logger.exception("Scheduled daily refresh failed")


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _run_daily_refresh,
        trigger=IntervalTrigger(hours=get_settings().refresh_interval_hours),
        id="daily_refresh",
    )
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
