import re

file_path = 'app/domain/models.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove ondelete='CASCADE' and ondelete='SET NULL'
content = re.sub(r",\s*ondelete='CASCADE'", "", content)
content = re.sub(r",\s*ondelete=\"CASCADE\"", "", content)
content = re.sub(r",\s*ondelete='SET NULL'", "", content)
content = re.sub(r",\s*ondelete=\"SET NULL\"", "", content)

# Check for cascade='all, delete-orphan' as well, but SQL Server handles SQLAlchemy cascading orphans in Python layer fine mostly
# It's specifically the DB-level FOREIGN KEY ON DELETE cascades that cause the multiple paths issue in SQL Server.

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed models.py foreign keys!")
