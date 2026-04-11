import sys
import os
import logging

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.infrastructure.database import engine
from app.migrations import run_startup_migrations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration_script")

def main():
    logger.info("Starting manual schema migration...")
    try:
        run_startup_migrations(engine)
        logger.info("Migration completed successfully.")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
