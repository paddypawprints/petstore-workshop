from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.pets import router as pets_router
from app.api.routes.store import router as store_router
from app.api.routes.users import router as users_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": settings.app_name, "status": "ok"}


app.include_router(health_router)
app.include_router(pets_router)
app.include_router(store_router)
app.include_router(users_router)
