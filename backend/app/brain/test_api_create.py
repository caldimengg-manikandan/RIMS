import requests
import json
import uuid

# Configuration
API_URL = "http://localhost:10000/api/jobs"
LOGIN_URL = "http://localhost:10000/api/auth/login"

def test_api_job_create():
    # 1. Login to get token
    login_data = {
        "email": "aashifanshaf786@gmail.com",
        "password": "password" # I hope this is the password
    }
    
    try:
        print(f"Logging in as {login_data['email']}...")
        response = requests.post(LOGIN_URL, json=login_data)
        if response.status_code != 200:
            print(f"Login failed: {response.text}")
            return
        
        token = response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        # 2. Create Job
        job_payload = {
            "title": "API Test Job " + uuid.uuid4().hex[:6],
            "description": "This is a test job created via the API endpoint script.",
            "experience_level": "junior",
            "domain": "Engineering",
            "primary_evaluated_skills": ["Testing", "API"],
            "aptitude_enabled": True,
            "aptitude_mode": "ai",
            "first_level_enabled": True,
            "interview_mode": "ai",
            "duration_minutes": 60
        }
        
        print(f"Creating job: {job_payload['title']}...")
        response = requests.post(API_URL, json=job_payload, headers=headers)
        
        if response.status_code == 201 or response.status_code == 200:
            print("Job created successfully via API!")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"Job creation failed with status {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Error during API test: {e}")

if __name__ == "__main__":
    test_api_job_create()
