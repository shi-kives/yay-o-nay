import numpy as np
import pandas as pd
from datetime import datetime
from collections import defaultdict
from scipy import stats
import spacy
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from wordcloud import WordCloud
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from transformers import pipeline as hf_pipeline
from sqlalchemy.orm import Session
from pipeline.models import Review, Prediction, AspectSentiment
import os
import logging

logger = logging.getLogger(__name__)

nlp = spacy.load("en_core_web_sm")
vader = SentimentIntensityAnalyzer()
embedder = SentenceTransformer("all-MiniLM-L6-v2")
summarizer = hf_pipeline("summarization", model="facebook/bart-large-cnn")

def extract_aspects(text):
    doc = nlp(text)
    pairs = []
    for chunk in doc.noun_chunks:
        aspect = chunk.root.text.lower()

        opinions = [child.text.lower() for child in chunk.root.children if child.dep_ == "amod"]

        if chunk.root.dep_ in ("nsubj", "dobj"):
            for sibling in chunk.root.head.children:
                if sibling.dep_ == "acomp":
                    opinions.append(sibling.text.lower())

        for opinion in opinions:
            pairs.append((aspect, opinion))

    return pairs

def score_aspect_sentiment(review_id, db):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        return
    
    pairs = extract_aspects(review.clean_text)
    words = review.clean_text.split()

    for aspect, opinion in pairs:
        try:
            idx = words.index(aspect)
        except ValueError:
            idx = 0
        
        start = max(0, idx - 3)
        end = min(len(words), idx + 4)
        window = " ".join(words[start:end])

        score = vader.polarity_scores(window)["compound"]

        row = AspectSentiment(
            review_id = review_id,
            asin = review.asin,
            aspect = aspect,
            opinion = opinion,
            vader_score = score
        )
        db.add(row)

    db.commit()

def get_product_score(asin, db):
    predictions = (
        db.query(Prediction, Review).join(Review, Review.id == Prediction.review_id).filter(Review.asin == asin).all()
    )
    if not predictions:
        return {"score": 0.0, "confidence": 0.0, "review_count": 0}
    
    now = datetime.now() # flag
    scores, weights = [], []

    for pred, review in predictions:
        sentiment_val = pred.score if pred.sentiment_label == "POSITIVE" else (1 - pred.score)
        days_ago = (now - review.created_at).days
        recency_w = np.exp(-0.01 * days_ago)

        scores.append(sentiment_val)
        weights.append(recency_w)

    scores = np.array(scores)
    weights = np.array(weights)

    raw_score = np.average(scores, weights = weights)
    volume_w = np.log1p(len(scores)) / 10
    final = min(raw_score * (1 + volume_w) * 10, 10.0)
    confidence = min(len(scores) / 100, 1.0)

    return {"score": round(final , 2), "confidence": round(confidence, 2), "review_count": len(scores)}

def get_aspect_summary(asin, db):
    rows = db.query(AspectSentiment).filter(AspectSentiment.asin == asin).all()

    if not rows:
        return {"top_positive": [], "top_negative": [], "all_aspects": {}, "confidence": 0.0}
    
    aspect_data = defaultdict(list)
    for row in rows:
        aspect_data[row.aspect].append(row.vader_score)

    summary = {}
    for aspect, scores in aspect_data.items():
        avg = np.mean(scores)
        summary[aspect] = {
            "avg_score": round(avg, 3),
            "mention_count": len(scores),
            "sentiment": "positive" if avg > 0 else "negative"
        }

    positives = sorted([a for a, v in summary.items() if v["sentiment"] == "positive"],
    key=lambda a: summary[a]["mention_count"], reverse=True)

    negatives = sorted([a for a, v in summary.items() if v["sentiment"] == "negative"],
    key = lambda a: summary[a]["mention_count"], reverse=True)   

    return {
        "top_positive": positives[:5],
        "top_negative": negatives[:5]
    }

def get_trends(asin, db):
    rows = (db.query(Prediction, Review).join(Review, Review.id == Prediction.review_id).filter(Review.asin == asin).all())

    if not rows:
        return []
    
    records = []
    for pred, review in rows:
        val = pred.score if pred.sentiment_label == "POSITIVE" else 1 - pred.score
        records.append({"date": review.created_at, "score": val})

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()

    weekly = df.resample("W").mean()
    rolling = weekly.rolling(4, min_periods = 1).mean()

    rolling["z"] = stats.zscore(rolling["score"].fillna(0))
    rolling["is_anomaly"] = rolling["z"].abs() > 2

    return [
        {
            "week": str(idx.date()),
            "avg_score": round(row["score"] * 10, 2),
            "is_anomaly": bool(row["is_anomaly"])
        } for idx, row in rolling.iterrows()
    ]

def summarize_reviews(asin, db):
    rows = (db.query(Review, Prediction).join(Prediction, Prediction.review_id == Review.id).filter(Review.asin == asin).order_by(Prediction.score.desc()).limit(10).all())

    if not rows:
        return "no reviews available to summarize"
    
    combined = " ".join([review.clean_text for review, _ in rows])
    combined = combined[:1024]

    result = summarizer(combined, max_length = 150, min_length = 40, do_sample = False)
    return result[0]["summary_text"]

def compare_products(asin_a, asin_b, db):
    def get_embedding(asin):
        reviews = db.query(Review).filter(Review.asin == asin).all()
        texts = [r.clean_text for r in reviews if r.clean_text]
        if not texts:
            return None
        vecs = embedder.encode(texts, show_progress_bar = False)
        return np.mean(vecs, axis = 0)
    
    emb_a = get_embedding(asin_a)
    emb_b = get_embedding(asin_b)
    if emb_a is None or emb_b is None:
        return {"similarity": 0.0, "error": "One or both products have no reviews"}
    
    similarity = cosine_similarity([emb_a], [emb_b])[0][0]
    return {"asin_a": asin_a, "asin_b": asin_b, "similarity": round(float(similarity), 3)}

def generate_wordcloud(asin, db):
    reviews = db.query(Review).filter(Review.asin == asin).all()
    texts = [r.clean_text for r in reviews if r.clean_text]
    if not texts:
        return ""
    
    tfidf = TfidfVectorizer(max_features=200, stop_words="english")
    matrix = tfidf.fit_transform(texts)
    scores = dict(zip(tfidf.get_feature_names_out(), matrix.sum(axis=0).tolist()[0]))

    wc = WordCloud(width = 800, height = 400, background_color="white").generate_from_frequencies(scores)

    os.makedirs("data/wordclouds", exist_ok=True)
    path = f"data/wordclouds/{asin}.png"
    wc.to_file(path)
    return path