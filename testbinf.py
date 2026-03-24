from pipeline.classifier import batch_inference
from pipeline.models import SessionLocal
db = SessionLocal()
for asin in ['B000000001','B000000002','B000000003','B000000004']:
    count = batch_inference(asin, db)
    print(f"{asin}: classified {count} reviews")
db.close()