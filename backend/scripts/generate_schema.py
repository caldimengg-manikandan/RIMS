
import sys
import os

# Add the backend directory to sys.path to allow imports from 'app'
sys.path.append(os.path.join(os.getcwd(), 'app'))
sys.path.append(os.getcwd())

from sqlalchemy import create_mock_engine
from app.infrastructure.database import Base
from app.domain import models

def dump(sql, *multiparams, **params):
    print(sql.compile(dialect=engine.dialect))

engine = create_mock_engine("postgresql://", dump)

print("-- RIMs Database Schema (PostgreSQL)")
print("-- Generated from SQLAlchemy models")
print()

Base.metadata.create_all(engine)
