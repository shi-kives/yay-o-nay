from dotenv import load_dotenv
import os
load_dotenv(override=True)

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import redis, json
from api.schemas import (UrlRequest, TextRequest, SentimentOut, ProductScore, Recommendation, TrendPoint, CompareResult, TaskStatus)
from api.middleware import APIKeyMiddleware
from pipeline.models import get_db
from pipeline.classifier import classify
from pipeline.components import (get_product_score, get_aspect_summary, get_trends, summarize_reviews, compare_products)
from pipeline.recommendation import get_recommendation
from pipeline.scraper import extract_asin
from tasks.inference import run_full_pipeline, celery_app


app = FastAPI(title="YayONay API", version="1.0")
#app.add_middleware(APIKeyMiddleware)

redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/analyze/url")
async def anaylze_url(req):
    try:
        asin = extract_asin(req.url)
    except ValueError:
        raise HTTPException(400, "Invalid Amazon URL, could not find product ASIN")
    task = run_full_pipeline.delay(asin)
    return {"task_id": task.id, "asin": asin, "status": "queued"}

@app.post("/analyze/text", response_model=SentimentOut)
async def analyze_text(req: TextRequest):
    return classify(req.text)

@app.get("/products/{asin}/score", response_model=ProductScore)
async def product_score(asin, db: Session = Depends(get_db)):
    cached = redis_client.get(f"score{asin}")
    if cached:
        return json.loads(cached)
    
    result = get_product_score(asin,db)
    result["asin"] = asin
    redis_client.setex(f"score:{asin}", 3600, json.dumps(result))
    return result

@app.get("/products/{asin}/recommendation", response_model=Recommendation)
async def recommendation(asin, db: Session = Depends(get_db)):
    return get_recommendation(asin, db)

@app.get("/products/{asin}/trends")
async def trends(asin, db: Session = Depends(get_db)):
    return get_trends(asin, db)

@app.get("/products/{asin}/aspects")
async def aspects(asin, db: Session = Depends(get_db)):
    return get_aspect_summary(asin, db)

@app.get("/products/{asin}/summary")
async def summary(asin, db: Session = Depends(get_db)):
    return {"summary": summarize_reviews(asin, db)}

@app.get("/compare", response_model=CompareResult)
async def compare(asin_a, asin_b, db: Session = Depends(get_db)):
    return compare_products(asin_a, asin_b, db)

@app.get("/tasks/{task_id}", response_model=TaskStatus)
async def task_status(task_id):
    task = celery_app.AsyncResult(task_id)
    status = task.status
    info = task.info if isinstance(task.info, dict) else {}
    result = task.result if status == "SUCCESS" else None
    return {"task_id": task_id, "status": status, "info": info, "result": result}