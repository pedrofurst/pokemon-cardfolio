from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.routers import cards, holdings, prices

ALLOWED_ORIGINS = ["http://localhost:3000"]


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


def create_application() -> FastAPI:
    application = FastAPI(title="Cardfolio API", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(cards.router)
    application.include_router(holdings.router)
    application.include_router(prices.router)

    @application.get("/health")
    def get_health() -> dict:
        return {"status": "ok"}

    return application


app = create_application()
