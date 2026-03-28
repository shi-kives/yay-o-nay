from celery import Celery
import os

celery_app = Celery(
    "yayonay",
    broker = os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend = os.getenv("REDIS_URL", "redis://localhost:6379/0")
)

@celery_app.task(bind=True)
def run_full_pipeline(self, asin):
    from pipeline.scraper import scrape_reviews
    from pipeline.ingest import store_reviews
    from pipeline.classifier import batch_inference
    from pipeline.components import (score_aspect_sentiment, generate_wordcloud)
    from pipeline.recommendation import get_recommendation
    from pipeline.models import SessionLocal, Review

    db = SessionLocal()
    try:
        self.update_state(state="PROGRESS", meta={"step": "scraping reviews"})
        reviews = scrape_reviews(asin, max_pages=5)
        if not reviews:
            return {"error": "could not scrape reviews -- amazon may have blocked the request"}
        
        self.update_state(state="PROGRESS", meta={"step": "storing reviews"})
        store_reviews(asin, reviews, db)

        self.update_state(state="PROGRESS", meta={"step": "running BERT"})
        batch_inference(asin, db)

        self.update_state(state="PROGRESS", meta={"step": "extracting aspects"})
        review_ids = [r.id for r in db.query(Review).filter(Review.asin == asin).all()]
        for rid in review_ids:
            score_aspect_sentiment(rid, db)

        self.update_state(state="PROGRESS", meta={"step": "generating verdict"})
        generate_wordcloud(asin, db)
        verdict = get_recommendation(asin, db)

        return {"status": "done", "asin": asin, "verdict": verdict}
    
    finally:
        db.close()