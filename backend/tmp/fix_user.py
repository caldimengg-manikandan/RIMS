import sys
import os
sys.path.append(os.getcwd())

from app.infrastructure.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("UPDATE users SET role = 'super_admin', approval_status = 'approved' WHERE email = 'caldiminternship@gmail.com'"))
    conn.commit()
    print("Promoted caldiminternship@gmail.com to super_admin")

    # Also backfill applications.hr_id if missing
    try:
        conn.execute(text("UPDATE applications SET hr_id = (SELECT hr_id FROM jobs WHERE jobs.id = applications.job_id) WHERE hr_id IS NULL"))
        conn.commit()
        print("Backfilled applications.hr_id")
    except:
        pass
