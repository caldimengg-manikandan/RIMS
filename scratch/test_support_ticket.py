import requests
import json

base_url = "http://localhost:8000"

payload = {
    "email": "test@example.com",
    "access_key": "dummy_key",
    "grievance_type": "technical",
    "description": "My browser crashed during the interview process, can you please assist?"
}

try:
    response = requests.post(f"{base_url}/api/support/ticket", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")
