import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load env
load_dotenv('backend/.env')

db_url = os.environ.get("DATABASE_URL")
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
session = Session()

from app.domain.models import Application

# Query applications where offer_token_used is True
used_tokens = session.query(Application).filter(Application.offer_token_used == True).all()
print(f"Candidates with offer_token_used=True: {len(used_tokens)}")
for c in used_tokens:
    print(f"ID: {c.id} | Name: {c.candidate_name} | Status: {c.status} | Response Status: {c.offer_response_status}")
