from fastapi import APIRouter, Depends

from app.deps import get_digest_service
from app.services.digest_service import DigestService

router = APIRouter(tags=["digest"])


@router.get("/digest")
def get_digest(service: DigestService = Depends(get_digest_service)) -> dict:
    return service.build()
