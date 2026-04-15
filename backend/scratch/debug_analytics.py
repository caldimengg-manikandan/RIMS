
import requests
import json

# Replace with local backend URL
BASE_URL = "http://localhost:10000"

def test_dashboard_analytics():
    try:
        # We still expect 401 without token, but I want to check if the route is defined and reachable.
        response = requests.get(f"{BASE_URL}/api/analytics/dashboard")
        print(f"Status: {response.status_code}")
        print(f"Body: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_dashboard_analytics()
