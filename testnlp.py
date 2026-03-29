from pipeline.models import SessionLocal, Review
from pipeline.components import score_aspect_sentiment, get_product_score, generate_wordcloud, summarize_reviews

db = SessionLocal()
asins = ['B000000001', 'B000000002', 'B000000003', 'B000000004']

for asin in asins:
    print(f"processing {asin}")
    review_ids = [r.id for r in db.query(Review).filter(Review.asin == asin).all()]
    for rid in review_ids:
        score_aspect_sentiment(rid, db)
    score = get_product_score(asin, db)
    wc_path = generate_wordcloud(asin, db)
    summary = summarize_reviews(asin, db)
    print(f"{asin} -> score: {score}, wordcloud: {wc_path}")

db.close()