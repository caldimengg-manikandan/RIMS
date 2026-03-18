from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
import logging
from typing import Dict
from .session_manager import session_manager
from .interview_controller import process_interview_message

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/ws/interview/{session_id}")
async def interview_websocket_endpoint(websocket: WebSocket, session_id: str, token: str):
    """WebSocket endpoint for real-time live interviews."""
    
    # In a real enterprise app, we'd verify the JWT token here
    # user = verify_token(token)
    user_id = "temp_user_id" # Placeholder
    
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
            
            # Delegate business logic to controller
            await process_interview_message(session_id, data)

    except WebSocketDisconnect:
        session_manager.disconnect(session_id)
        logger.info(f"WebSocket closed for session: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error in session {session_id}: {str(e)}", exc_info=True)
        session_manager.disconnect(session_id)
