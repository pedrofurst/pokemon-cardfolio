from fastapi import Depends
from sqlmodel import Session

from app.config import get_settings
from app.db import get_session
from app.providers.fx_provider import FxProvider
from app.providers.pokemontcgio import PokemonTcgIoProvider
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.price_repository import PriceRepository
from app.repositories.sale_repository import SaleRepository
from app.repositories.watch_repository import WatchRepository
from app.services.collection_service import CollectionService
from app.services.digest_service import DigestService
from app.services.grading_service import GradingService
from app.services.insights_service import InsightsService
from app.services.opportunity_service import OpportunityService
from app.services.price_check_service import PriceCheckService
from app.services.price_service import PriceService
from app.services.sale_service import SaleService
from app.services.store_service import StoreService

# Single long-lived provider (and its underlying httpx.Client) reused across
# requests instead of constructing a new client per request.
_provider = PokemonTcgIoProvider(api_key=get_settings().pokemontcg_api_key)
_fx_provider = FxProvider()


def get_collection_service(session: Session = Depends(get_session)) -> CollectionService:
    return CollectionService(
        CardRepository(session), HoldingRepository(session), PriceRepository(session),
        PortfolioRepository(session),
    )


def get_portfolio_repository(session: Session = Depends(get_session)) -> PortfolioRepository:
    return PortfolioRepository(session)


def get_price_repository(session: Session = Depends(get_session)) -> PriceRepository:
    return PriceRepository(session)


def get_price_service(session: Session = Depends(get_session)) -> PriceService:
    return PriceService(
        CardRepository(session), PriceRepository(session),
        _provider, HoldingRepository(session), WatchRepository(session),
    )


def get_price_check_service(session: Session = Depends(get_session)) -> PriceCheckService:
    return PriceCheckService(_provider, PriceRepository(session))


def get_opportunity_service(session: Session = Depends(get_session)) -> OpportunityService:
    return OpportunityService(
        CardRepository(session), PriceRepository(session),
        HoldingRepository(session), WatchRepository(session),
    )


def get_grading_service() -> GradingService:
    return GradingService()


def get_fx_provider() -> FxProvider:
    return _fx_provider


def get_insights_service(session: Session = Depends(get_session)) -> InsightsService:
    return InsightsService(
        CardRepository(session), HoldingRepository(session), PriceRepository(session),
    )


def get_sale_service(session: Session = Depends(get_session)) -> SaleService:
    return SaleService(
        HoldingRepository(session), SaleRepository(session), CardRepository(session),
    )


def get_store_service() -> StoreService:
    return StoreService(_provider)


def get_digest_service(session: Session = Depends(get_session)) -> DigestService:
    card_repo = CardRepository(session)
    holding_repo = HoldingRepository(session)
    price_repo = PriceRepository(session)
    portfolio_repo = PortfolioRepository(session)
    watch_repo = WatchRepository(session)
    sale_repo = SaleRepository(session)
    return DigestService(
        CollectionService(card_repo, holding_repo, price_repo, portfolio_repo),
        OpportunityService(card_repo, price_repo, holding_repo, watch_repo),
        SaleService(holding_repo, sale_repo, card_repo),
        portfolio_repo,
    )
