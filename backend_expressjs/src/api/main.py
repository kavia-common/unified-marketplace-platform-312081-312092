import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text

from src.api.db import db_session, get_engine
from src.api.routes import router as api_router
from src.api.seed import seed_if_empty

openapi_tags = [
    {"name": "health", "description": "Service health and status endpoints."},
    {"name": "auth", "description": "Authentication and user identity endpoints (JWT)."},
    {"name": "stores", "description": "Storefront store endpoints."},
    {"name": "products", "description": "Storefront product endpoints."},
    {"name": "cart", "description": "Server-side cart (placeholder)."},
    {"name": "orders", "description": "Order creation and listing endpoints."},
]

app = FastAPI(
    title="Unified Marketplace Backend",
    description=(
        "Multi-vendor marketplace backend API.\n\n"
        "Auth: Use `Authorization: Bearer <token>` for protected endpoints.\n"
        "Key endpoints expected by frontend:\n"
        "- GET /api/health\n"
        "- GET /api/stores, GET /api/stores/{id}\n"
        "- GET /api/products, GET /api/products/{id}\n"
        "- GET/POST/PATCH /api/cart\n"
        "- POST/GET /api/orders\n"
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",") if os.getenv("ALLOWED_ORIGINS") else ["*"]
allowed_headers = os.getenv("ALLOWED_HEADERS", "*").split(",") if os.getenv("ALLOWED_HEADERS") else ["*"]
allowed_methods = os.getenv("ALLOWED_METHODS", "*").split(",") if os.getenv("ALLOWED_METHODS") else ["*"]
cors_max_age = int(os.getenv("CORS_MAX_AGE", "3600"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins],
    allow_credentials=True,
    allow_methods=[m.strip() for m in allowed_methods],
    allow_headers=[h.strip() for h in allowed_headers],
    max_age=cors_max_age,
)

app.include_router(api_router, prefix="/api")


@app.on_event("startup")
def _startup() -> None:
    """
    Initialize DB connectivity and optionally seed demo data.

    Notes:
    - We do not auto-run alembic migrations here (production should run migrations explicitly).
      We only validate DB connectivity and allow optional seeding for local/demo environments.
    - The platform may not provide DATABASE_URL in some environments (e.g., preview/CI).
      In that case, we skip DB checks so the service can still boot and serve /api/health.
    """
    engine = get_engine()
    if engine is None:
        # DB not configured; keep service up for health checks and non-DB endpoints.
        return

    # quick connectivity check
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    if os.getenv("SEED_ON_STARTUP", "false").lower() == "true":
        with db_session() as db:
            seed_if_empty(db)
