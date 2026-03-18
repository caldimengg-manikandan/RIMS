import os
import subprocess

print("Step 1: Creating database if not exists...")
sub = subprocess.run(["venv/Scripts/python", "scripts/create_db.py"], capture_output=True, text=True)

print(sub.stdout)
if sub.returncode != 0:
    print(sub.stderr)
    print("Failed to create database. Please verify your DATABASE_URL credentials in .env and try again.")
    exit(1)

print("Step 2: Database verified. Running Alembic migrations to populate tables...")
sub2 = subprocess.run(["venv/Scripts/alembic.exe", "upgrade", "head"], capture_output=True, text=True)


print(sub2.stdout)
if sub2.returncode != 0:
    print(sub2.stderr)
    print("Failed to execute Alembic migrations on MySQL.")
    exit(1)

print("MySQL Schema migration completed successfully!")
