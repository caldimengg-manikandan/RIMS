"""Quick backend API email test — logs in as admin, hits /api/ops/email/test."""
import json
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE = "http://127.0.0.1:10000"
TO_EMAIL = sys.argv[1] if len(sys.argv) > 1 else "pradeepmuthuselvan08@gmail.com"

# Step 1: Login to get JWT (need admin creds — try reading from DB or use existing)
# Since the /test endpoint requires admin, let's directly call the SMTP send
# function instead, bypassing auth.

import os, sys
from pathlib import Path
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("BACKEND_START_MODE", "script")

from dotenv import load_dotenv
load_dotenv(BACKEND / ".env", override=False)

import asyncio
from app.core.config import get_settings
# Clear the LRU cache so it picks up new env
get_settings.cache_clear()
settings = get_settings()

print(f"SMTP_USER loaded: {settings.smtp_user}")
print(f"SMTP_PASSWORD: {'*' * len(settings.smtp_password)} ({len(settings.smtp_password)} chars)")
print(f"Sending to: {TO_EMAIL}")
print()

from app.services.email_service import send_email_async

async def main():
    result = await send_email_async(
        TO_EMAIL,
        "RIMS Backend Email Test ✅",
        "<html><body><h2>RIMS Backend Test</h2><p>This email was sent through the full <code>send_email_async()</code> pipeline.</p></body></html>",
    )
    print(json.dumps(result, indent=2))
    if result.get("success"):
        print(f"\n✅ Email delivered via {result.get('provider', 'unknown')} — check {TO_EMAIL} inbox!")
    else:
        print(f"\n❌ Failed: {result.get('error')}")
        if result.get("deferred"):
            print("   ⏳ Gmail quota hit — try again in 24h or use a different account")

asyncio.run(main())
