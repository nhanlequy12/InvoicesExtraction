from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.v1 import api_v1_router
from src.core.config import settings
from src.core.database import Base, engine
from src.core.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    logger.info("Initializing database schemas...")
    Base.metadata.create_all(bind=engine)
    logger.info(f"{settings.APP_NAME} started successfully in {settings.APP_ENV} environment.")
    yield
    logger.info("Application shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise Vietnamese E-Invoice Automated Processing, Validation & Accounting Integration Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 Router
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "env": settings.APP_ENV,
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
