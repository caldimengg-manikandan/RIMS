import sqlite3

def run():
    conn = sqlite3.connect('sql_app.db')
    c = conn.cursor()
    
    # Adding new metadata columns to the jobs table
    try:
        c.execute("ALTER TABLE jobs ADD COLUMN location VARCHAR(255) DEFAULT 'Remote'")
        print("Added location column to jobs.")
    except Exception as e:
        print(f"Location column might already exist: {e}")
        
    try:
        c.execute("ALTER TABLE jobs ADD COLUMN job_type VARCHAR(50) DEFAULT 'Full-Time'")
        print("Added job_type column to jobs.")
    except Exception as e:
        print(f"job_type column might already exist: {e}")
        
    try:
        c.execute("ALTER TABLE jobs ADD COLUMN department VARCHAR(100) DEFAULT 'Engineering'")
        print("Added department column to jobs.")
    except Exception as e:
        print(f"department column might already exist: {e}")
        
    conn.commit()
    conn.close()
    print("Database migration for job metadata successful.")

if __name__ == '__main__':
    run()
