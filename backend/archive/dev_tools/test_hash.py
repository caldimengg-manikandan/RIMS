import traceback
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

try:
    pwd_context.hash("password123")
    print("OK hash works")
except Exception as e:
    traceback.print_exc()

import sys
sys.path.append("d:/Caldim/RIMS-main/RIMS-main/backend")

from app.core.auth import hash_password

try:
    print("Testing hash_password...")
    res = hash_password("password123")
    print("hash_password works! len=" + str(len(res)))
except Exception as e:
    traceback.print_exc()

from app.api.auth import hash_password as api_auth_hash
try:
    print("Testing api.auth.hash_password...")
    res = api_auth_hash("password123")
    print("api.auth.hash_password works! len=" + str(len(res)))
except Exception as e:
    traceback.print_exc()
