import requests
import json

base_url = "http://localhost:10000/api"

try:
    # Login or get session token first if Auth required
    # But usually listed lists are guarded by Depends(get_current_user)
    # Let's see if we can login with ID 1 email
    print("Logging in with caldiminternship@gmail.com...")
    login_req = requests.post(f"{base_url}/auth/login", json={"email": "caldiminternship@gmail.com", "password": "password"}) # wait, password might be different!
    print(f"Login Response {login_req.status_code}: {login_req.text}")
    
except Exception as e:
    print(f"Failed to fetch endpoints: {e}")
