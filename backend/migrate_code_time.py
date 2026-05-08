import os
import re

def migrate_codebase():
    root_dir = r"c:\Users\user\Desktop\RIMS\rims\backend\app"
    pattern = re.compile(r"datetime\.now\(timezone\.utc\)")
    import_line = "from app.core.timezone import get_ist_now"
    
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                if "datetime.now(timezone.utc)" in content:
                    print(f"Updating {path}")
                    # Replace occurrences
                    new_content = content.replace("datetime.now(timezone.utc)", "get_ist_now()")
                    
                    # Add import if missing
                    if import_line not in new_content:
                        # Add after existing imports
                        lines = new_content.splitlines()
                        inserted = False
                        for i, line in enumerate(lines):
                            if line.startswith("from ") or line.startswith("import "):
                                continue
                            else:
                                lines.insert(i, import_line)
                                inserted = True
                                break
                        if not inserted:
                            lines.append(import_line)
                        new_content = "\n".join(lines)
                    
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(new_content)

if __name__ == "__main__":
    migrate_codebase()
