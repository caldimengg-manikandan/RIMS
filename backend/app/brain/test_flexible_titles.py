import requests
import json
import uuid

# Configuration (Port 10000 per start.ps1)
API_URL = "http://localhost:10000/api/jobs"
LOGIN_URL = "http://localhost:10000/api/auth/login"

def test_flexible_titles():
    # 1. Login
    login_data = {
        "email": "aashifanshaf786@gmail.com",
        "password": "password"
    }
    
    try:
        print(f"Logging in as {login_data['email']}...")
        response = requests.post(LOGIN_URL, json=login_data)
        if response.status_code != 200:
            print(f"Login failed: {response.text}")
            return
        
        token = response.json().get("data", {}).get("access_token")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        # 2. Test flexible title (with colons, ampersands, etc.)
        flexible_title = "Lead Dev: Python & AI Engineer! (Remote #1) + Senior"
        
        job_payload = {
            "title": flexible_title,
            "description": "This job has a very flexible title with many special characters to test the new validation rules.",
            "experience_level": "senior",
            "domain": "Engineering",
            "primary_evaluated_skills": ["Python", "AI"],
            "aptitude_enabled": False, # Aptitude only for junior/intern
            "first_level_enabled": True,
            "interview_mode": "ai"
        }
        
        print(f"Attempting to create job with flexible title: '{flexible_title}'...")
        response = requests.post(API_URL, json=job_payload, headers=headers)
        
        if response.status_code < 400:
            print("SUCCESS: Flexible title job created!")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"FAILURE: Job creation failed with status {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Error during flexible title test: {e}")

if __name__ == "__main__":
    test_flexible_titles()
