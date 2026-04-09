import os
import asyncio
from dotenv import load_dotenv
import httpx
import smtplib
from email.mime.text import MIMEText

load_dotenv()

async def test_groq():
    api_key = os.getenv("GROQ_API_KEY")
    print(f"Testing Groq with key: {api_key[:10]}...")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": "Hello, are you working?"}],
        "max_tokens": 10
    }
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            print(f"Groq Response Status: {resp.status_code}")
            print(f"Groq Response Body: {resp.text}")
        except Exception as e:
            print(f"Groq Error: {e}")

def test_email():
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", 587))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM", user)
    
    print(f"Testing Email: {user} via {host}:{port}...")
    
    msg = MIMEText("This is a test email from RIMS.")
    msg["Subject"] = "RIMS Test Email"
    msg["From"] = sender
    msg["To"] = user # Send to self
    
    try:
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        print("Email Sent Successfully!")
    except Exception as e:
        print(f"Email Error: {e}")

if __name__ == "__main__":
    print("--- STARTING TESTS ---")
    asyncio.run(test_groq())
    test_email()
    print("--- TESTS FINISHED ---")
