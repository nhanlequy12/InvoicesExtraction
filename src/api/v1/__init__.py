from fastapi import APIRouter
from .ingestion import router as ingestion_router
from .invoices import router as invoices_router
from .reviews import router as reviews_router
from .export import router as export_router

api_v1_router = APIRouter()
api_v1_router.include_router(ingestion_router)
api_v1_router.include_router(invoices_router)
api_v1_router.include_router(reviews_router)
api_v1_router.include_router(export_router)
