import psycopg2
import sys
import os
from cryptography.fernet import Fernet, InvalidToken

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from app.core.config import get_settings

def sanitize_database():
    settings = get_settings()
    key = settings.encryption_key
    print(f"Using ENCRYPTION_KEY: {key[:5]}...{key[-5:]}")
    
    try:
        f = Fernet(key)
    except Exception as e:
        print(f"Error initializing Fernet: {e}")
        return

    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()
    
    # Tables and columns to check (EncryptedText fields)
    targets = [
        ("applications", ["candidate_phone", "candidate_phone_raw", "hr_notes"]),
        ("application_stages", ["evaluation_notes"]),
        ("resume_extractions", ["extracted_text"]),
        ("interview_answers", ["answer_text", "answer_evaluation"]),
        ("interview_reports", ["summary", "strengths", "weaknesses", "detailed_feedback"]),
        ("hiring_decisions", ["decision_comments"]),
        ("notifications", ["message"]),
        ("audit_logs", ["details"])
    ]

    for table, columns in targets:
        print(f"\nScanning table: {table}")
        for col in columns:
            cursor.execute(f"SELECT id, {col} FROM {table} WHERE {col} IS NOT NULL")
            rows = cursor.fetchall()
            
            corrupted_ids = []
            for row_id, value in rows:
                if value and value.startswith("gAAAAA"):
                    try:
                        f.decrypt(value.encode())
                    except InvalidToken:
                        corrupted_ids.append(row_id)
                    except Exception as e:
                        print(f"Unknown error at {table}.{col} ID {row_id}: {e}")
            
            if corrupted_ids:
                print(f"  [!] Found {len(corrupted_ids)} corrupted records in {col}. Handling...")
                # Use subquery or bulk update with placeholder for non-nullable col
                placeholder = "[DECRYPTION_FAILED_DUE_TO_KEY_MISMATCH]"
                cursor.execute(f"UPDATE {table} SET {col} = %s WHERE id IN %s", (placeholder, tuple(corrupted_ids),))
                conn.commit()
            else:
                print(f"  [OK] {col} is clean.")

    cursor.close()
    conn.close()
    print("\nDatabase sanitization complete.")

if __name__ == "__main__":
    sanitize_database()
