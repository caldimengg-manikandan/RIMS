import sqlite3

def run():
    conn = sqlite3.connect('sql_app.db')
    c = conn.cursor()
    c.execute("PRAGMA foreign_keys=off;")
    
    # Create the new table without candidate_id
    c.execute('''
    CREATE TABLE interviews_new (
        id INTEGER NOT NULL, 
        application_id INTEGER NOT NULL, 
        status VARCHAR(50) NOT NULL, 
        locked_skill VARCHAR(255), 
        total_questions INTEGER, 
        questions_asked INTEGER, 
        overall_score FLOAT, 
        started_at DATETIME, 
        ended_at DATETIME, 
        access_key_hash VARCHAR(255),
        expires_at DATETIME,
        is_used BOOLEAN DEFAULT 0,
        used_at DATETIME,
        created_at DATETIME, 
        updated_at DATETIME, 
        PRIMARY KEY (id), 
        FOREIGN KEY(application_id) REFERENCES applications (id) ON DELETE CASCADE
    )
    ''')
    
    # Copy data over
    c.execute('''
    INSERT INTO interviews_new (id, application_id, status, locked_skill, total_questions, questions_asked, overall_score, started_at, ended_at, access_key_hash, expires_at, is_used, used_at, created_at, updated_at)
    SELECT id, application_id, status, locked_skill, total_questions, questions_asked, overall_score, started_at, ended_at, access_key_hash, expires_at, is_used, used_at, created_at, updated_at
    FROM interviews
    ''')
    
    c.execute("DROP TABLE interviews")
    c.execute("ALTER TABLE interviews_new RENAME TO interviews")
    
    try:
        c.execute("CREATE INDEX ix_interviews_id ON interviews (id)")
        c.execute("CREATE INDEX ix_interviews_application_id ON interviews (application_id)")
        c.execute("CREATE INDEX ix_interviews_status ON interviews (status)")
    except Exception as e:
        print(f"Index creation error: {e}")
    
    conn.commit()
    conn.close()
    print("Database interviews migration successful. candidate_id has been removed.")

if __name__ == '__main__':
    run()
