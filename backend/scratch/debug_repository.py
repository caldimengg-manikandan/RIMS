
import requests
import json
import sys

# Replace with your local backend URL
BASE_URL = "http://localhost:10000"

# Mock login or use a known token if possible.
# Since I don't have a token, I'll just check if the endpoint is reachable.
def test_sets():
    try:
        # We expect a 401 if we don't have a token, but let's see if it crashes before that.
        # Although get_current_hr is a dependency, so it will check auth FIRST.
        response = requests.get(f"{BASE_URL}/api/repository/sets")
        print(f"Status: {response.status_code}")
        print(f"Body: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_sets()
