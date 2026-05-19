import os
import httpx
from dotenv import load_dotenv

load_dotenv('backend/.env')

# Let's call the API endpoint by querying the database directly first to find a candidate,
# or we can construct a test client call using FastAPI test client.
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import create_access_token

# Let's find an HR user to generate a token
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.domain.models import User

engine = create_engine(os.environ.get("DATABASE_URL"))
Session = sessionmaker(bind=engine)
session = Session()

hr = session.query(User).filter(User.role == "hr").first()
token = create_access_token(data={"sub": str(hr.id), "role": "hr"})

client = TestClient(app)
response = client.get("/api/onboarding/candidates", headers={"Authorization": f"Bearer {token}"})
print(f"Status code: {response.status_code}")
data = response.json()
items = data.get("items", [])
print(f"Items count: {len(items)}")
if items:
    first = items[0]
    print("First item keys and values:")
    for k, v in first.items():
        print(f"  {k}: {v} (type: {type(v).__name__})")
