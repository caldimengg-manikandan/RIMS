import os
import sys
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(env_path)

# Add the current directory to the python path to import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.infrastructure.database import engine
from sqlalchemy import text

with engine.begin() as conn:
    try:
        conn.execute(text("ALTER TABLE resume_extractions ADD COLUMN candidate_name VARCHAR(255)"))
        print("Added candidate_name")
    except Exception as e:
        print("candidate_name:", e)
    
    try:
        conn.execute(text("ALTER TABLE resume_extractions ADD COLUMN email VARCHAR(255)"))
        print("Added email")
    except Exception as e:
        print("email:", e)
        
    try:
        conn.execute(text("ALTER TABLE resume_extractions ADD COLUMN phone_number VARCHAR(50)"))
        print("Added phone_number")
    except Exception as e:
        print("phone_number:", e)

print("Finished altering table.")
