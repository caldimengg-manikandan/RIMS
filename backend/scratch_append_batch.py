with open(r'C:\Users\user\Desktop\PROJECT\rims\backend\app\services\email_ingestion_service.py', 'a', encoding='utf-8') as f:
    f.write('''\n
import os
import requests
from typing import List

def run_batch_resume_processing(db: Session):
    """
    Finds all unprocessed resumes in the database, downloads them into a local 
    folder for batch analysis, and marks them as processed so they aren't processed again.
    """
    unprocessed = db.query(AttachmentResume).filter(AttachmentResume.processed == False).all()
    
    if not unprocessed:
        return {"message": "No new resumes to process.", "count": 0}
        
    # Create the batch folder
    batch_folder = os.path.join(os.getcwd(), "batch_analysis_inbox")
    os.makedirs(batch_folder, exist_ok=True)
    
    downloaded_count = 0
    
    for resume in unprocessed:
        if not resume.file_url:
            resume.processed = True  # Skip ones without URLs
            continue
            
        try:
            # Download the file from Supabase public URL
            response = requests.get(resume.file_url, stream=True)
            if response.status_code == 200:
                safe_filename = f"candidate_{resume.id}_{resume.file_name}"
                file_path = os.path.join(batch_folder, safe_filename)
                
                with open(file_path, 'wb') as pdf_file:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            pdf_file.write(chunk)
                
                # Mark as processed in DB so we never run it again
                resume.processed = True
                downloaded_count += 1
        except Exception as e:
            logger.error(f"Failed to download {resume.file_url}: {e}")
            
    db.commit()
    return {"message": f"Successfully downloaded {downloaded_count} new resumes to {batch_folder} for batch analysis.", "count": downloaded_count}
''')
