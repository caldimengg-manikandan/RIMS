#!/usr/bin/env python
"""
Database initialization script.
Run this once to create all tables and seed initial data.
"""

import sys
from sqlalchemy import create_engine, text
from app.config import get_settings
from app.models import Base, User
from app.database import SessionLocal
from app.auth import hash_password
import os
import traceback

settings = get_settings()

def init_database():
    """Create all tables and seed initial data"""
    try:
        # Create engine
        engine = create_engine(settings.database_url)
        
        # Create all tables
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully")
        
        # Seed initial data
        print("\nSeeding initial data...")
        db = SessionLocal()
        
        try:
            # Check if demo users already exist
            candidate = db.query(User).filter(User.email == "candidate@example.com").first()
            if not candidate:
                # Create candidate user
                candidate = User(
                    email="candidate@example.com",
                    password_hash=hash_password("password123"),
                    full_name="John Doe",
                    role="candidate",
                    is_active=True
                )
                db.add(candidate)
                print("Created candidate user: candidate@example.com")
            
            # Check if HR user exists
            hr_user = db.query(User).filter(User.email == "hr@example.com").first()
            if not hr_user:
                # Create HR user
                hr_user = User(
                    email="hr@example.com",
                    password_hash=hash_password("password12345"),
                    full_name="Jane Smith",
                    role="hr",
                    is_active=True
                )
                db.add(hr_user)
                print("Created HR user: hr@example.com")
            
            db.commit()
            print("\nDatabase initialization completed successfully!")
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"\nError initializing database: {str(e)}")
        traceback.print_exc()
        print(f"\nMake sure:")
        print(f"  1. Database path is writable")
        print(f"  2. DATABASE_URL in .env is correct")
        sys.exit(1)

if __name__ == "__main__":
    init_database()
