import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.getcwd())

from app.core.config import get_settings
from app.services.email_service import send_simple_email

async def test_email():
    settings = get_settings()
    target = "klx2m164jr@lnovic.com"
    print(f"Attempting to send test email to {target}...")
    print(f"SMTP User: {settings.smtp_user}")
    
    success = await send_simple_email(
        target,
        "System Test: Email Functionality Restored",
        "This is a test message to verify that email triggers have been successfully restored in the RIMS system."
    )
    
    if success:
        print("\nSUCCESS: Email sent successfully!")
    else:
        print("\nFAILED: Email could not be sent. Check backend logs for errors.")

if __name__ == "__main__":
    asyncio.run(test_email())
