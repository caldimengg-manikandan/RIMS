import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import json
from datetime import datetime

# Load env
load_dotenv('backend/.env')

db_url = os.environ.get("DATABASE_URL")
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
session = Session()

from app.domain.models import Application
from fastapi.encoders import jsonable_encoder

candidates = session.query(Application).filter(
    Application.status.in_(["hired", "pending_approval", "offer_sent", "accepted", "onboarded"])
).limit(5).all()

encoded = jsonable_encoder(candidates)
for c in encoded:
    print(f"ID: {c.get('id')} | Name: {c.get('candidate_name')} | joining_date: {repr(c.get('joining_date'))}")
