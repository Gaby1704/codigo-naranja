import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings, validate_runtime_settings
from app.db import init_db
from app.routers import auth, dashboard, datasets
from app.services.accounts import seed_admin

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    validate_runtime_settings(settings)
    logger.info(
        "Iniciando API Código Naranja (env=%s, backend=%s, origins=%d, cookie_secure=%s, samesite=%s)",
        settings.app_env,
        settings.db_backend,
        len(settings.allowed_origins),
        settings.effective_cookie_secure,
        settings.effective_cookie_samesite,
    )
    init_db()
    seed_admin()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Código Naranja API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Codigo-Naranja"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store"
        if settings.effective_cookie_secure:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_payload(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": "Los datos enviados no son válidos."})

    @app.exception_handler(Exception)
    async def unexpected(_request: Request, exc: Exception) -> JSONResponse:
        if getattr(exc, "status_code", None):
            detail = getattr(exc, "detail", "No se pudo completar la solicitud.")
            if not isinstance(detail, str):
                detail = "No se pudo completar la solicitud."
            return JSONResponse(status_code=exc.status_code, content={"detail": detail})
        logger.exception("Error no controlado")
        return JSONResponse(status_code=500, content={"detail": "No se pudo completar la solicitud."})

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(datasets.router, prefix="/api")
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    runtime = get_settings()
    uvicorn.run("app.main:app", host=runtime.host, port=runtime.port)
