import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class SessionManager:
    """Manages Active WebSocket sessions for live interviews"""
    def __init__(self):
        # Maps session_id -> WebSocket
        self.active_sessions: Dict[str, any] = {}
        # Maps user_id -> session_id
        self.user_to_session: Dict[str, str] = {}

    async def connect(self, session_id: str, user_id: str, websocket):
        await websocket.accept()
        self.active_sessions[session_id] = websocket
        self.user_to_session[user_id] = session_id
        logger.info(f"Session {session_id} connected for user {user_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        # remove user mapping
        to_del_user = next((uid for uid, sid in self.user_to_session.items() if sid == session_id), None)
        if to_del_user:
            del self.user_to_session[to_del_user]
        logger.info(f"Session {session_id} disconnected")

    async def send_personal_message(self, message: dict, session_id: str):
        websocket = self.active_sessions.get(session_id)
        if websocket:
            await websocket.send_json(message)
        else:
            logger.warning(f"Attempted to send message to inactive session: {session_id}")

    def get_session(self, session_id: str):
        return self.active_sessions.get(session_id)

session_manager = SessionManager()
