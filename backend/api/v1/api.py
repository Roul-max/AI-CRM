from fastapi import APIRouter
from .endpoints import interactions, chat

api_router = APIRouter()
api_router.include_router(interactions.router, prefix="/interactions", tags=["Interactions"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat Agent"])