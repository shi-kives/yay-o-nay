from pipeline.models import SessionLocal
from pipeline.recommendation import get_recommendation

db = SessionLocal()
result = get_recommendation('B000000002', db)
print(result)
db.close()