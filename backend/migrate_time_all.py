from app.infrastructure.database import engine
from sqlalchemy import text, inspect

def migrate():
    with engine.connect() as conn:
        try:
            print("Running comprehensive time migration to IST...")
            
            # List of (table, [columns]) to shift
            targets = [
                ("applications", ["updated_at", "parsing_started_at", "last_attempt_at"]),
                ("interviews", ["started_at", "ended_at", "used_at", "created_at", "updated_at", "aptitude_completed_at", "expires_at"]),
                ("jobs", ["created_at", "updated_at", "closed_at"]),
                ("interview_issues", ["created_at", "resolved_at"]),
                ("application_stages", ["created_at", "started_at", "completed_at"]),
                ("interview_reports", ["created_at"]),
                ("notifications", ["created_at"]),
                ("audit_logs", ["created_at"]),
                ("resume_extractions", ["created_at", "updated_at"]),
                ("interview_feedbacks", ["created_at"])
            ]

            inspector = inspect(engine)
            
            for table, columns in targets:
                if not inspector.has_table(table):
                    continue
                
                existing_cols = [c["name"] for c in inspector.get_columns(table)]
                cols_to_shift = [c for c in columns if c in existing_cols]
                
                if not cols_to_shift:
                    continue
                
                set_clause = ", ".join([f"{col} = {col} + interval '5 hours 30 minutes'" for col in cols_to_shift])
                sql = f"UPDATE {table} SET {set_clause}"
                
                # Note: applied_at in applications was already shifted in previous step, 
                # but for safety let's assume we are running this fresh or we handle it.
                # Actually, if I run it again on applied_at, it will double-shift.
                # I'll add a check or just skip applied_at if it was already done.
                # But to be simple, I'll just shift everything EXCEPT what I already shifted if I can.
                
                print(f"  Shifting {table}: {', '.join(cols_to_shift)}")
                conn.execute(text(sql))
            
            conn.commit()
            print("Migration OK: Database is now fully IST-based.")
        except Exception as e:
            print(f"Migration error: {e}")

if __name__ == "__main__":
    migrate()
