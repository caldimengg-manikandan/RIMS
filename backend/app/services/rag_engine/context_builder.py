import uuid
from app.services.rag_engine.vector_store import VectorStore

class ContextBuilder:
    """
    Retrieval Augmented Generation (RAG) Context Builder.
    Responsible for ingesting resumes and job descriptions, and retrieving them
    as ground-truth context for the AI Interviewer Agent.
    """
    
    def __init__(self, session_id: str):
        # Isolate collections per interview session
        self.session_id = session_id
        self.job_store = VectorStore(f"job_context_{self.session_id}")
        self.resume_store = VectorStore(f"resume_context_{self.session_id}")
        self.question_store = VectorStore(f"question_context_{self.session_id}")

    def ingest_job_description(self, jd_text: str, skills: list[str]):
        """Splits and ingests job description and required skills into the vector DB."""
        # Chunking (For simplicity, chunk by paragraphs. In prod, use RecursiveCharacterTextSplitter)
        chunks = [c.strip() for c in jd_text.split('\n\n') if c.strip()]
        for i, chunk in enumerate(chunks):
            self.job_store.add_document(f"jd_chunk_{i}", chunk, {"source": "job_description", "session_id": self.session_id})
            
        if skills:
            skills_text = "Required Skills: " + ", ".join(skills)
            self.job_store.add_document("jd_skills", skills_text, {"source": "required_skills", "session_id": self.session_id})

    def ingest_candidate_resume(self, resume_text: str):
        """Ingests chunks of the candidate's parsed resume."""
        chunks = [c.strip() for c in resume_text.split('\n\n') if len(c.strip()) > 20]
        for i, chunk in enumerate(chunks):
            self.resume_store.add_document(f"resume_chunk_{i}", chunk, {"source": "candidate_resume", "session_id": self.session_id})

    def get_interview_context(self, current_question_topic: str) -> str:
        """
        Retrieves top RAG context from both the Job Description and the Candidate Resume 
        relevant to the current interview question topic.
        """
        # Retrieve top 2 chunks from JD and top 2 chunks from Resume
        jd_context = self.job_store.query_context(current_question_topic, n_results=2)
        resume_context = self.resume_store.query_context(current_question_topic, n_results=2)
        
        context_parts = []
        if jd_context:
            context_parts.append("--- JOB CONTEXT ---")
            context_parts.extend(jd_context)
            
        if resume_context:
            context_parts.append("--- CANDIDATE RESUME CONTEXT ---")
            context_parts.extend(resume_context)
            
        if not context_parts:
            return "No specific context available."
            
        return "\n\n".join(context_parts)
