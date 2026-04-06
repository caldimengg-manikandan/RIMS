import logging

logger = logging.getLogger(__name__)

class SessionManager:
    """
    Manages the lifecycle of an active AI interviewer session,
    tying together the candidate, database IDs, and connection meta.
    """
    def __init__(self, db_session):
        self.db = db_session
        self.active_sessions = {}

    def start_interview_session(self, candidate_id: int, job_id: int) -> dict:
        """
        Registers a new interview session in memory and the DB.
        """
        session_id = f"{candidate_id}_{job_id}_session"
        self.active_sessions[session_id] = {
            "candidate_id": candidate_id,
            "job_id": job_id,
            "current_difficulty": "medium",
            "score": 0.0,
            "questions_asked": 0
        }
        
        # In a real app, this also creates an `InterviewSession` SQL row
        logger.info(f"[SessionManager] Started Session: {session_id}")
        return self.active_sessions[session_id]

    def get_session(self, session_id: str) -> dict:
        return self.active_sessions.get(session_id)
        
    def end_interview_session(self, session_id: str):
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"[SessionManager] Ended Session: {session_id}")
