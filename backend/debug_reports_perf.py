import cProfile
import pstats
import io
import os
from dotenv import load_dotenv
from app.infrastructure.database import SessionLocal
from app.api.analytics import get_interview_reports
from app.domain.models import User

load_dotenv()

def profile_reports():
    db = SessionLocal()
    user = db.query(User).filter(User.role == 'super_admin').first()
    if not user:
        print("No super_admin user found.")
        return

    pr = cProfile.Profile()
    pr.enable()
    
    res = get_interview_reports(skip=0, limit=50, current_user=user, db=db)
    
    pr.disable()
    s = io.StringIO()
    sortby = 'cumulative'
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats(30)  # Print top 30 functions
    print(s.getvalue())

if __name__ == '__main__':
    profile_reports()
