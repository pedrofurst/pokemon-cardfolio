import dataclasses

from fastapi import APIRouter, Depends

from app.deps import get_store_service
from app.services.store_service import StoreService

router = APIRouter(prefix="/store", tags=["store"])


@router.get("")
def get_store(service: StoreService = Depends(get_store_service)) -> dict:
    boosters = service.build()
    return {"boosters": [dataclasses.asdict(booster) for booster in boosters]}
