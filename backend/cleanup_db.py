import os
import time

files = ["../sql_app.db", "../sql_app.db-shm", "../sql_app.db-wal"]
for file in files:
    if os.path.exists(file):
        try:
            os.remove(file)
            print(f"Removed {file}")
        except Exception as e:
            print(f"Failed to remove {file}: {e}")
    else:
        print(f"{file} does not exist")
