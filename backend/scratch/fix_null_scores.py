import psycopg2
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from app.core.config import get_settings

def fix_null_scores():
    settings = get_settings()
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()
    
    try:
        print("Patching NULL scores in applications table...")
        # Update scores to 0.0 where they are currently NULL
        cursor.execute("""
            UPDATE applications 
            SET 
                resume_score = COALESCE(resume_score, 0.0),
                aptitude_score = COALESCE(aptitude_score, 0.0),
                interview_score = COALESCE(interview_score, 0.0),
                composite_score = COALESCE(composite_score, 0.0)
            WHERE 
                resume_score IS NULL OR 
                aptitude_score IS NULL OR 
                interview_score IS NULL OR 
                composite_score IS NULL
        """)
        
        affected = cursor.rowcount
        conn.commit()
        print(f"Success: Patched {affected} applications with NULL scores.")
    except Exception as e:
        print(f"Error patching scores: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    fix_null_scores()
