from fastapi import APIRouter
from backend.api.v1.endpoints import interactions, chat

api_router = APIRouter()
api_router.include_router(interactions.router, prefix="/interactions", tags=["interactions"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
