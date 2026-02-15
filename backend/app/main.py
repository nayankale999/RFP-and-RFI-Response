import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.shared.exceptions import RFPAutomationError
from app.api import auth, projects, documents, requirements, responses, export, pricing, generate
from app.database import engine, Base
import app.models  # noqa: F401 - Import models so Base.metadata knows about all tables

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Enterprise RFP/RFI Response Automation API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3020", "http://127.0.0.1:3020"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler for application errors
@app.exception_handler(RFPAutomationError)
async def rfp_error_handler(request: Request, exc: RFPAutomationError):
    return JSONResponse(
        status_code=400,
        content={"error": exc.message, "detail": exc.detail},
    )


# Register routers
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(requirements.router)
app.include_router(responses.router)
app.include_router(export.router)
app.include_router(pricing.router)
app.include_router(generate.router)


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": settings.app_name}


@app.on_event("startup")
async def startup():
    logger.info(f"Starting {settings.app_name}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")


@app.on_event("shutdown")
async def shutdown():
    await engine.dispose()
    logger.info("Application shutdown complete")
