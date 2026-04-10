import psycopg2
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from app.core.config import get_settings

def sync_template():
    settings = get_settings()
    
    # 1. Read a.html
    html_path = os.path.join(os.getcwd(), 'a.html')
    if not os.path.exists(html_path):
        print(f"Error: {html_path} not found.")
        return
        
    with open(html_path, 'r', encoding='utf-8') as f:
        template_content = f.read()

    # 2. Update database
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO global_settings (key, value, updated_at) "
            "VALUES ('offer_letter_template', %s, NOW()) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()",
            (template_content,)
        )
        conn.commit()
        print("Success: Offer letter template updated from a.html.")
    except Exception as e:
        print(f"Error syncing template: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    sync_template()
