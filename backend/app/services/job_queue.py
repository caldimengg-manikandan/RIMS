from typing import Dict, Any

# Simple in-memory dict for job tracking
ai_jobs: Dict[str, Dict[str, Any]] = {}

def create_job(job_id: str):
    ai_jobs[job_id] = {"status": "processing", "result": None, "error": None}

def complete_job(job_id: str, result: Any = None):
    if job_id in ai_jobs:
        ai_jobs[job_id]["status"] = "completed"
        ai_jobs[job_id]["result"] = result

def fail_job(job_id: str, error: str):
    if job_id in ai_jobs:
        ai_jobs[job_id]["status"] = "failed"
        ai_jobs[job_id]["error"] = error

def get_job(job_id: str):
    return ai_jobs.get(job_id)
