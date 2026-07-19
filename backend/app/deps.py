from fastapi import Depends
from sqlmodel import Session

from app.config import get_settings
from app.db import get_session
from app.providers.pokemontcgio import PokemonTcgIoProvider
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository
from app.repositories.watch_repository import WatchRepository
from app.services.collection_service import CollectionService
from app.services.grading_service import GradingService
from app.services.opportunity_service import OpportunityService
from app.services.price_service import PriceService

# Single long-lived provider (and its underlying httpx.Client) reused across
# requests instead of constructing a new client per request.
_provider = PokemonTcgIoProvider(api_key=get_settings().pokemontcg_api_key)


def get_collection_service(session: Session = Depends(get_session)) -> CollectionService:
    return CollectionService(
        CardRepository(session), HoldingRepository(session), PriceRepository(session),
    )


def get_price_service(session: Session = Depends(get_session)) -> PriceService:
    return PriceService(
        CardRepository(session), PriceRepository(session),
        _provider, HoldingRepository(session), WatchRepository(session),
    )


def get_opportunity_service(session: Session = Depends(get_session)) -> OpportunityService:
    return OpportunityService(
        CardRepository(session), PriceRepository(session),
        HoldingRepository(session), WatchRepository(session),
    )


def get_grading_service() -> GradingService:
    return GradingService()
