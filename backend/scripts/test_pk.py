import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")

if not db_url:
    print("DATABASE_URL not found")
    exit(1)

print(f"Connecting to: {db_url}")
engine = create_engine(db_url)

try:
    with engine.connect() as connection:
        query = "ALTER TABLE interview_issues MODIFY id INT AUTO_INCREMENT PRIMARY KEY"
        connection.execute(text(query))
        connection.commit()
    print("Succeeded on interview_issues PK layout!")
except Exception as e:
    print(f"Failed: {e}")
