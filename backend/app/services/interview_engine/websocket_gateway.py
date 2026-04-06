import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.auth import verify_token
from app.core.config import get_settings
from .interview_controller import process_interview_message
from .session_manager import session_manager

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

# Serialize message handling per session so rapid client sends cannot overlap evaluate/generate work.
_session_locks: dict[str, asyncio.Lock] = {}


def _session_lock(session_id: str) -> asyncio.Lock:
    if session_id not in _session_locks:
        _session_locks[session_id] = asyncio.Lock()
    return _session_locks[session_id]

@router.websocket("/ws/interview/{session_id}")
async def interview_websocket_endpoint(websocket: WebSocket, session_id: str, token: str):
    """WebSocket endpoint for real-time live interviews."""
    user_id = "temp_user_id"

    if settings.ws_enforce_interview_jwt:
        if not token or not str(token).strip():
            await websocket.close(code=1008)
            return
        try:
            payload = verify_token(token)
            role = payload.get("role")
            sub = payload.get("sub")
            if role != "interview" or sub is None:
                await websocket.close(code=1008)
                return

            # Enforce session binding when session_id is numeric interview id
            if str(session_id).isdigit() and str(sub) != str(session_id):
                await websocket.close(code=1008)
                return
            user_id = f"interview_{sub}"
        except Exception:
            await websocket.close(code=1008)
            return
    
    await session_manager.connect(session_id, user_id, websocket)
    
    try:
        # Initial greeting and first question
        await session_manager.send_personal_message(
            {"type": "system", "message": "Connected to AI Interview Engine. Preparing your first question..."},
            session_id
        )
        await process_interview_message(session_id, {"action": "start"})

        while True:
            # Receive text/json from candidate
            data = await websocket.receive_json()

            # One in-flight controller turn per session (queues on client still help UX; this guards the engine).
            async with _session_lock(session_id):
                await process_interview_message(session_id, data)

    except WebSocketDisconnect:
        session_manager.disconnect(session_id)
        logger.info(f"WebSocket closed for session: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error in session {session_id}: {str(e)}", exc_info=True)
        session_manager.disconnect(session_id)
