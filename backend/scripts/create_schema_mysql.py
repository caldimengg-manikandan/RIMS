import sys
import os

sys.path.insert(0, os.getcwd())


from app.infrastructure.database import Base, engine
# Import all models to populate metadata
from app.domain.models import *

print("Attempting to create all tables in MySQL database...")
try:
    Base.metadata.create_all(bind=engine)
    print("Successfully created all tables in MySQL!")
except Exception as e:
    print(f"Failed to create tables: {e}")
    sys.exit(1)
