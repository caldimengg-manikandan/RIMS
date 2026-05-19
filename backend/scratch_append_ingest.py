with open(r'C:\Users\user\Desktop\PROJECT\rims\backend\app\api\applications.py', 'a', encoding='utf-8') as f:
    f.write('''\n
from app.services.email_ingestion_service import fetch_resume_attachments
from pydantic import BaseModel

class EmailIngestRequest(BaseModel):
    imap_user: str
    imap_pass: str

@router.post("/ingest-emails")
def ingest_email_resumes(req: EmailIngestRequest, db: Session = Depends(get_db)):
    """
    Trigger manual email ingestion via IMAP
    """
    result = fetch_resume_attachments(db, req.imap_user, req.imap_pass)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return {"message": "Ingestion complete", "saved_count": result.get("count")}
''')
