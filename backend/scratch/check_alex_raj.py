import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://postgres.itajqbrebdbrunfqpbmg:Caldim%402026@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_application():
    db = SessionLocal()
    try:
        # Search for Alex Raj
        print("Searching for application: Alex Raj")
        query = text("""
            SELECT id, candidate_name, candidate_email, status, applied_at 
            FROM applications 
            WHERE candidate_name ILIKE :name 
            ORDER BY applied_at DESC 
            LIMIT 5
        """)
        results = db.execute(query, {"name": "%Alex Raj%"}).fetchall()
        
        if not results:
            print("No application found for Alex Raj.")
            return

        for app in results:
            print(f"\n--- Application ID: {app.id} ---")
            print(f"Name: {app.candidate_name}")
            print(f"Email: {app.candidate_email}")
            print(f"Status: {app.status}")
            print(f"Applied At: {app.applied_at}")
            
            # Check audit logs for emails
            print("\nChecking Audit Logs for actions/transitions:")
            audit_query = text("""
                SELECT action, details, created_at 
                FROM audit_logs 
                WHERE resource_id = :id AND resource_type = 'Application'
                ORDER BY created_at ASC
            """)
            logs = db.execute(audit_query, {"id": app.id}).fetchall()
            for log in logs:
                print(f"[{log.created_at}] Action: {log.action}")
                if log.details:
                    print(f"  Details: {log.details}")

            # Check notifications (which often trigger emails)
            print("\nChecking Notifications for HR:")
            notif_query = text("""
                SELECT notification_type, title, message, created_at 
                FROM notifications 
                WHERE related_application_id = :id
                ORDER BY created_at ASC
            """)
            notifs = db.execute(notif_query, {"id": app.id}).fetchall()
            for n in notifs:
                print(f"[{n.created_at}] Type: {n.notification_type} | Title: {n.title}")

            # Check EMAIL AUDIT LOGS
            print("\nChecking Email Audit Logs (Global):")
            # Note: email audits might not be linked by ID if ID was None, so we search by action
            email_audit_query = text("""
                SELECT action, details, created_at 
                FROM audit_logs 
                WHERE resource_type = 'Email'
                ORDER BY created_at DESC
                LIMIT 20
            """)
            email_logs = db.execute(email_audit_query).fetchall()
            for elog in email_logs:
                # Details contains the hash of the email
                print(f"[{elog.created_at}] Action: {elog.action} | Details: {elog.details}")

    finally:
        db.close()

if __name__ == "__main__":
    check_application()
