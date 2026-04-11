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

class SessionLockManager:
    """
    Manages per-session asyncio locks with explicit cleanup to prevent memory leaks.
    Architected to be easily swappable with a Redis-based distributed lock for horizontal scaling.
    """
    def __init__(self):
        self._locks: dict[str, asyncio.Lock] = {}

    def get_lock(self, session_id: str) -> asyncio.Lock:
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()
        return self._locks[session_id]

    def release_lock(self, session_id: str):
        """Cleanup lock entry from memory for closed sessions."""
        if session_id in self._locks:
            # We only delete if the lock is not currently held to be safe, 
            # though disconnect logic usually implies no more messages.
            if not self._locks[session_id].locked():
                del self._locks[session_id]

lock_manager = SessionLockManager()

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
            async with lock_manager.get_lock(session_id):
                await process_interview_message(session_id, data)

    except WebSocketDisconnect:
        session_manager.disconnect(session_id)
        lock_manager.release_lock(session_id)
        logger.info(f"WebSocket closed for session: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error in session {session_id}: {str(e)}", exc_info=True)
        session_manager.disconnect(session_id)
        lock_manager.release_lock(session_id)
