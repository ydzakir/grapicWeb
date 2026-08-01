from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.v1.alerts import router as alerts_router
from api.v1.auth import router as auth_router
from api.v1.cloudflare import router as cloudflare_router
from api.v1.cluster import router as cluster_router
from api.v1.collectors import router as collectors_router
from api.v1.datacenters import router as datacenters_router
from api.v1.governance import router as governance_router
from api.v1.metrics import router as metrics_router
from api.v1.nodes import router as nodes_router
from api.v1.reports import router as reports_router
from api.v1.secrets import router as secrets_router
from api.v1.topology import router as topology_router
from api.v1.users import router as users_router
from api.v1.ws import router as ws_router
from core.config import settings
from core.database import AsyncSessionLocal
from services.auth_service import bootstrap_admin_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Bootstrap initial admin user on startup if in dev/prod
    if settings.ENVIRONMENT != "testing":
        async with AsyncSessionLocal() as db:
            try:
                await bootstrap_admin_user(db)
                await db.commit()
            except Exception as e:
                await db.rollback()
                print(f"Warning: Admin bootstrap failed: {e}")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url=None,
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else ["http://localhost", "https://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Consistent error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail},
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": str(exc.detail),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation error",
                "details": jsonable_encoder(exc.errors()),
            }
        },
    )


# Register routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(collectors_router, prefix="/api/v1")
app.include_router(nodes_router, prefix="/api/v1")
app.include_router(datacenters_router, prefix="/api/v1")
app.include_router(topology_router, prefix="/api/v1")
app.include_router(metrics_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(cloudflare_router, prefix="/api/v1")
app.include_router(cluster_router, prefix="/api/v1")
app.include_router(secrets_router, prefix="/api/v1")
app.include_router(governance_router, prefix="/api/v1")
app.include_router(ws_router)



@app.get("/api/v1/health/live", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_liveness():
    """Liveness probe."""
    return {"status": "live", "service": "infra-monitoring-backend"}


@app.get("/api/v1/health/ready", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_readiness():
    """Readiness probe."""
    return {
        "status": "ready",
        "service": "infra-monitoring-backend",
        "environment": settings.ENVIRONMENT,
    }
