
import sqlite3
import os

db_path = r'd:\CALDIM\ars\RIMS\backend\sql_app.db'

def migrate():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Checking current status of 'applications' table...")
    
    try:
        # Disable foreign keys during migration
        cursor.execute("PRAGMA foreign_keys=OFF")
        
        # Start transaction
        cursor.execute("BEGIN TRANSACTION")
        
        # 1. Create new table with updated constraints
        # I'll include all the statuses I added to models.py
        cursor.execute("""
        CREATE TABLE applications_new (
            id INTEGER NOT NULL, 
            job_id INTEGER NOT NULL, 
            candidate_name VARCHAR(255) NOT NULL, 
            candidate_email VARCHAR(255) NOT NULL, 
            candidate_phone TEXT, 
            resume_file_path VARCHAR(500), 
            resume_file_name VARCHAR(255), 
            candidate_photo_path VARCHAR(500), 
            status VARCHAR(50), 
            hr_notes TEXT, 
            resume_score FLOAT, 
            aptitude_score FLOAT, 
            interview_score FLOAT, 
            composite_score FLOAT, 
            recommendation VARCHAR(50), 
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
            PRIMARY KEY (id), 
            CONSTRAINT check_applications_status CHECK (status IN (
                'applied', 'submitted', 'resume_screening', 'aptitude_round', 'ai_interview', 
                'technical_interview', 'hr_interview', 'physical_interview', 'final_decision', 
                'hired', 'rejected', 'processing_failed', 'approved_for_interview', 
                'review_later', 'rejected_post_interview'
            )), 
            CONSTRAINT uq_application_job_email UNIQUE (job_id, candidate_email), 
            FOREIGN KEY(job_id) REFERENCES jobs (id)
        )
        """)
        
        # 2. Copy data from old to new, converting 'submitted' to 'applied' if it exists
        cursor.execute("""
        INSERT INTO applications_new (
            id, job_id, candidate_name, candidate_email, candidate_phone,
            resume_file_path, resume_file_name, candidate_photo_path,
            status, hr_notes, resume_score, aptitude_score,
            interview_score, composite_score, recommendation,
            applied_at, updated_at
        )
        SELECT 
            id, job_id, candidate_name, candidate_email, candidate_phone,
            resume_file_path, resume_file_name, candidate_photo_path,
            CASE WHEN status = 'submitted' THEN 'applied' ELSE status END,
            hr_notes, resume_score, aptitude_score,
            interview_score, composite_score, recommendation,
            applied_at, updated_at
        FROM applications
        """)
        
        # 3. Drop old table
        cursor.execute("DROP TABLE applications")
        
        # 4. Rename new table
        cursor.execute("ALTER TABLE applications_new RENAME TO applications")
        
        # 5. Recreate indexes
        cursor.execute("CREATE INDEX ix_applications_composite_score ON applications (composite_score)")
        cursor.execute("CREATE INDEX ix_applications_job_id ON applications (job_id)")
        cursor.execute("CREATE INDEX ix_applications_status ON applications (status)")
        cursor.execute("CREATE INDEX ix_applications_applied_at ON applications (applied_at)")
        cursor.execute("CREATE INDEX ix_applications_candidate_email ON applications (candidate_email)")
        cursor.execute("CREATE INDEX ix_applications_job_status ON applications (job_id, status)")
        cursor.execute("CREATE INDEX ix_applications_id ON applications (id)")
        
        # Commit transaction
        conn.commit()
        print("Migration successful: applications table updated.")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
    finally:
        cursor.execute("PRAGMA foreign_keys=ON")
        conn.close()

if __name__ == "__main__":
    if os.path.exists(db_path):
        migrate()
    else:
        print(f"Database not found at {db_path}")
