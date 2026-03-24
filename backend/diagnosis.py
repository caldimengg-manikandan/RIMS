from app.infrastructure.database import SessionLocal
from app.domain.models import Job, User, Application
db = SessionLocal()
output_lines = []
try:
    job = db.query(Job).filter(Job.id == 2).first()
    if job:
        output_lines.append(f"Job 2: ID={job.id}, Title='{getattr(job, 'title', 'N/A')}', HR_ID={getattr(job, 'hr_id', 'N/A')}")
    else:
        output_lines.append("Job 2 not found")
        
    user = db.query(User).filter(User.id == 3).first()
    if user:
        output_lines.append(f"User 3: ID={user.id}, Email='{getattr(user, 'email', 'N/A')}', Role='{getattr(user, 'role', 'N/A')}'")
    else:
        output_lines.append("User 3 not found")
        
    emails = ['revathinagarajan1997@gmail.com', 'aashifanshaf786@gmail.com', 'mail@deepmehta.co.in']
    for email in emails:
        apps = db.query(Application).filter(Application.job_id == 2, Application.candidate_email == email).all()
        output_lines.append(f"Applications for Job 2 & {email}: Count={len(apps)}")
        if apps:
            for app in apps:
                 output_lines.append(f"  Existing App - ID: {app.id}, Status: {app.status}, Name: {app.candidate_name}")
finally:
    db.close()

with open("diagnosis_output.txt", "w") as f:
    f.write("\n".join(output_lines))
print("Output written to diagnosis_output.txt")
