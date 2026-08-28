from fastapi import APIRouter

from app.api.v1.endpoints import (
    attachments,
    auth,
    comments,
    health,
    organizations,
    projects,
    tasks,
    teams,
    ws,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health & Diagnostics"])
api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(teams.router)
api_router.include_router(projects.router)
api_router.include_router(tasks.router)
api_router.include_router(comments.router)
api_router.include_router(attachments.router)
api_router.include_router(ws.router)
