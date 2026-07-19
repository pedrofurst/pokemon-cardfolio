from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ALLOWED_ORIGINS = ["http://localhost:3000"]


def create_application() -> FastAPI:
    application = FastAPI(title="Cardfolio API")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/health")
    def get_health() -> dict:
        return {"status": "ok"}

    return application


app = create_application()
