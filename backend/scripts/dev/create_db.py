from app.domain.models import Base
from app.infrastructure.database import engine
import traceback
import sys

print("Creating tables in MySQL...")
try:
    Base.metadata.create_all(engine)
    print("Tables created successfully!")
except Exception as e:
    print("Error creating tables:")
    traceback.print_exc(file=sys.stdout)
