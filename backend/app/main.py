import logging
import warnings
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import close_pool, init_pool, persistence_enabled
from .migrate import run_migrations
from .readyz import readiness
from .routes.admin import router as admin_router
from .routes.chat import router as chat_router


def _silence_third_party_warnings() -> None:
    """langchain'in structured output cevabini serilestirirken urettigi pydantic
    uyarisini kapatir. Zararsiz (AIMessage.parsed alaninin tip anotasyonundan
    kaynaklaniyor) ama her router cagrisinda stderr'e dusuyor ve prod log'unu
    okunamaz hale getiriyor."""
    warnings.filterwarnings("ignore", message="Pydantic serializer warnings")


def _configure_logging(level: str) -> None:
    logging.basicConfig(level=level.upper(), format="%(message)s")
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            # format_exc_info olmadan log.exception() JSON'a yalnizca
            # "exc_info": true yaziyordu; hatanin kendisi log'a hic dusmuyordu.
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    _configure_logging(settings.LOG_LEVEL)
    _silence_third_party_warnings()
    await init_pool()
    if not persistence_enabled():
        structlog.get_logger().warning(
            "persistence_disabled",
            detail="MODE=local; sohbet geçmişi ve chat_logs DB'ye yazılmayacak.",
        )
    else:
        # Servis vermeden ONCE. Push = otomatik deploy oldugu icin migration'lar
        # elle uygulandiginda kod, semasindan once canliya cikabiliyordu; artik
        # cikamaz. Hata bilerek yutulmuyor: bozuk bir migration'da konteyner ayaga
        # kalkmasin. Bilinen yanlis bir semayla servis vermek, hic vermemekten kotu.
        yeni = await run_migrations()
        if yeni:
            structlog.get_logger().info("migrations_applied", versions=yeni)
    yield
    await close_pool()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Portfolio RAG Backend", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key"],
    )

    app.include_router(chat_router)
    app.include_router(admin_router)

    # /healthz: surec ayakta mi. Docker HEALTHCHECK bunu kullaniyor, bilerek
    # hicbir dis bagimliliga dokunmuyor — bkz. app/readyz.py docstring'i.
    @app.get("/healthz")
    async def healthz() -> dict:
        return {"status": "ok"}

    # /readyz: bagimliliklar gercekten calisiyor mu. Deploy sonrasi "indi mi,
    # dogru korpusa mi bakiyor" sorusunu /chat'e istek atmadan cevapliyor.
    @app.get("/readyz")
    async def readyz(response: Response) -> dict:
        govde, hazir = await readiness()
        if not hazir:
            response.status_code = 503
        return govde

    return app


app = create_app()
