import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import json

# Load env
load_dotenv('backend/.env')

db_url = os.environ.get("DATABASE_URL")
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
session = Session()

from app.domain.models import Application
from fastapi.encoders import jsonable_encoder

candidate = session.query(Application).filter(Application.id == 245).first()
if candidate:
    encoded = jsonable_encoder(candidate)
    print(json.dumps(encoded, indent=2))
