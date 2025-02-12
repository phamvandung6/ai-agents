from fastapi import APIRouter

from src.api.v1 import agent, auth

api_router = APIRouter()

# Auth routes
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["auth"],
)

# Agent routes
api_router.include_router(
    agent.router,
    prefix="/agent",
    tags=["agent"],
)
