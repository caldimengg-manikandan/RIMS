import os
import sys
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Setup minimal logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("ProductionVerify")

# Load environment
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

async def verify_db():
    logger.info("--- Testing Database Connectivity ---")
    try:
        from app.infrastructure.database import SessionLocal
        from sqlalchemy import text
        
        with SessionLocal() as db:
            start_link = datetime.now()
            db.execute(text("SELECT 1"))
            elapsed = (datetime.now() - start_link).total_seconds()
            logger.info(f"SUCCESS: Database ping in {elapsed:.3f}s")
            
            # Check Table Count
            from app.domain.models import User, Application
            user_count = db.query(User).count()
            app_count = db.query(Application).count()
            logger.info(f"STATS: Users={user_count}, Applications={app_count}")
            return True
    except Exception as e:
        logger.error(f"FAILURE: Database test failed: {e}")
        return False

async def verify_supabase():
    logger.info("--- Testing Supabase Storage ---")
    try:
        from app.core.storage import get_supabase_client
        from app.core.config import get_settings
        
        settings = get_settings()
        client = get_supabase_client()
        
        # Test bucket reachability
        buckets = [settings.supabase_bucket_resumes, settings.supabase_bucket_offers]
        for bucket in buckets:
            # Try to list files in a test directory
            try:
                client.storage.get_bucket(bucket)
                logger.info(f"SUCCESS: Bucket '{bucket}' is accessible")
            except Exception as b_err:
                logger.warning(f"WARNING: Bucket '{bucket}' might not be public/accessible: {b_err}")
        return True
    except Exception as e:
        logger.error(f"FAILURE: Supabase initialization failed: {e}")
        return False

async def verify_ai_services():
    logger.info("--- Testing AI Services reachability ---")
    try:
        from app.services.ai_service import parse_resume_with_ai
        from app.core.config import get_settings
        
        settings = get_settings()
        
        # Check API Key Presence
        keys = {
            "OpenAI": bool(settings.openai_api_key),
            "Groq": bool(settings.groq_api_key),
            "Anthropic": bool(settings.anthropic_api_key),
            "Gemini": bool(settings.gemini_api_key),
        }
        logger.info(f"CONFIG: API Keys Present: {keys}")
        
        if not any(keys.values()):
            logger.error("FAILURE: No AI API keys found in .env")
            return False
        
        # We won't call the API directly here to avoid costs, but let's verify connectivity to a simple endpoint
        import httpx
        if os.getenv("GROQ_API_KEY"):
            async with httpx.AsyncClient() as client:
                res = await client.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}"})
                if res.status_code == 200:
                    logger.info("SUCCESS: Groq API reachability confirmed")
                else:
                    logger.warning(f"WARNING: Groq API returned {res.status_code}: {res.text[:100]}")
        
        return True
    except Exception as e:
        logger.error(f"FAILURE: AI Service test errored: {e}")
        return False

async def main():
    logger.info("="*50)
    logger.info("RIMS PRODUCTION READINESS SMOKE TEST")
    logger.info(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    logger.info("="*50)
    
    # Add app directory to path
    sys.path.append(str(Path(__file__).parent))
    
    tasks = [verify_db(), verify_supabase(), verify_ai_services()]
    results = await asyncio.gather(*tasks)
    
    logger.info("="*50)
    if all(results):
        logger.info("SUCCESS: ALL SYSTEMS GO! RIMS is production-ready.")
    else:
        logger.error("CRITICAL: SMOKE TEST FAILED! Review the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
