from sqlalchemy.orm import Session
from pipeline.components import get_product_score, get_aspect_summary

def get_recommendation(asin, db):
    score_data = get_product_score(asin, db)
    aspect_data = get_aspect_summary(asin, db)

    score = score_data["score"]
    confidence = score_data["confidence"]
    positives = aspect_data["top_positive"]
    negatives = aspect_data["top_negative"]

    pos_str = ", ".join(positives[:3]) if positives else "general quality"
    neg_str = ", ".join(negatives[:3]) if negatives else "minor complaints"

    if score >= 7.5:
        verdict = "Yay!"
        label = "Buy!"
        reason = f"Strong positive reviews, majorly on the aspects: {pos_str}"

    elif score >= 5.5:
        verdict = "Yay!"
        label = "Buy with Caution!"
        reason = f"Mixed reviews, known for: {pos_str}, but problems with: {neg_str}"

    else:
        verdict = "Nay!"
        label = "Avoid"
        reason = f"Mostly negative reviews, majorly on the aspects: {neg_str}"

    return {"verdict": verdict, "label": label, "score": score, "reason": reason, "confidence": confidence, "positives": positives[:5], "negatives": negatives[:5]}
