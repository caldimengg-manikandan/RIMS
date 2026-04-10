import psycopg2
import sys
import os
from cryptography.fernet import Fernet, InvalidToken

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from app.core.config import get_settings

def check_encryption():
    settings = get_settings()
    key = settings.encryption_key
    print(f"Current ENCRYPTION_KEY: {key[:5]}...{key[-5:]}")
    
    try:
        f = Fernet(key)
    except Exception as e:
        print(f"Error initializing Fernet with current key: {e}")
        return

    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()
    
    print("\n--- Checking Global Settings ---")
    cursor.execute("SELECT key, value FROM global_settings")
    for k, v in cursor.fetchall():
        if v and v.startswith("gAAAAA"):
            try:
                f.decrypt(v.encode())
                print(f"[OK] {k} is encrypted and decryptable.")
            except InvalidToken:
                print(f"[FAIL] {k} is encrypted but INVALID TOKEN with current key. Length: {len(v)}")
                print(f"       Preview: {v[:20]}...")
            except Exception as e:
                print(f"[ERR] {k}: {e}")
        else:
            print(f"[SKIP] {k} is not encrypted.")

    print("\n--- Checking Application Fields (Sample) ---")
    cursor.execute("SELECT id, candidate_name, candidate_phone FROM applications LIMIT 5")
    for app_id, name, phone in cursor.fetchall():
        if phone and phone.startswith("gAAAAA"):
            try:
                f.decrypt(phone.encode())
                # print(f"[OK] App {app_id} ({name}) phone is decryptable.")
            except InvalidToken:
                print(f"[FAIL] App {app_id} ({name}) phone is INVALID TOKEN.")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_encryption()
