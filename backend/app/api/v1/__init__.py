from fastapi import APIRouter
from app.api.v1.research import router as research_router

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(research_router, prefix="/research", tags=["Research"])

__all__ = ["api_v1_router"]
