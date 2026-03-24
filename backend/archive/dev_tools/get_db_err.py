import traceback
from app.domain.models import Base
from app.infrastructure.database import engine

try:
    Base.metadata.create_all(engine)
except Exception as e:
    with open('error_out.txt', 'w', encoding='utf-8') as f:
        f.write(traceback.format_exc())
