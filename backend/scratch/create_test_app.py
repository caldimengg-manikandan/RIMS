import psycopg2

db_url = 'postgresql://postgres.itajqbrebdbrunfqpbmg:Caldim%402026@aws-1-ap-south-1.pooler.supabase.com:6543/postgres'

def create_test_app():
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Candidate: AASHIF SHADIN K N (ID: 154 in resume_extractions)
        # Job ID: 52 (Software Developer)
        query = """
            INSERT INTO applications (candidate_name, candidate_email, job_id, status, resume_score) 
            VALUES (%s, %s, %s, %s, %s) 
            RETURNING id
        """
        cur.execute(query, ('AASHIF SHADIN K N', 'aashifanshaf786@gmail.com', 52, 'applied', 85))
        app_id = cur.fetchone()[0]
        conn.commit()
        print(f"SUCCESS: Application created with ID: {app_id}")
        cur.close()
        conn.close()
        return app_id
    except Exception as e:
        print(f"FAILURE: {e}")
        return None

if __name__ == "__main__":
    create_test_app()
