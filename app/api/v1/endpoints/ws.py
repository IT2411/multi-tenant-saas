import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.core.database import session_manager
from app.core.security import decode_jwt_token
from app.models.project import Project
from app.repositories.organization import OrganizationMemberRepository
from app.websockets.hub import ws_hub

router = APIRouter(prefix="/ws", tags=["Real-Time WebSockets"])


@router.websocket("/projects/{project_id}")
async def project_realtime_stream(
    websocket: WebSocket,
    project_id: uuid.UUID,
    token: str = Query(...),
) -> None:
    """Secured real-time WebSocket channel streaming project task and comment updates."""
    # 1. Authenticate JWT token parameter
    try:
        payload = decode_jwt_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        user_id = uuid.UUID(payload["sub"])
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. Authorize Project & Organization Membership
    async with session_manager.sessionmaker() as session:
        project = await session.get(Project, project_id)
        if not project:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        member_repo = OrganizationMemberRepository(session)
        membership = await member_repo.get_membership(project.organization_id, user_id)
        if not membership:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    # 3. Connect to Hub
    await ws_hub.connect(project_id, websocket)
    try:
        while True:
            # Keepalive listener / Ping-Pong
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_hub.disconnect(project_id, websocket)
