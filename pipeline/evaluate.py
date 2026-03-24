import mlflow
from sklearn.metrics import (accuracy_score, f1_score, confusion_matrix, classification_report)
from pipeline.models import Review, Prediction, SessionLocal

def evaluate_pretrained(asin="B000000001", sample = 200):

    db = SessionLocal()
    rows = (
        db.query(Review, Prediction).join(Prediction, Prediction.review_id == Review.id).filter(Review.asin == asin).limit(sample).all()
    )
    db.close()

    if not rows:
        print("no predictions found. run batch_inference() first.")
        return
    
    y_true = [1 if review.rating == 5.0 else 0 for review, _ in rows]
    y_pred = [1 if pred.sentiment_label == "POSITIVE" else 0 for _, pred in rows]

    acc = accuracy_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred, average="macro")
    cm = confusion_matrix(y_true, y_pred)
    report = classification_report(y_true, y_pred, target_names=["NEGATIVE","POSITIVE"])

    print("\n----REPORT-----\n")
    print(f"samples evaluated: {len(rows)}")
    print(f"accuracy: {acc:.4f}")
    print(f"f1 macro: {f1:.4f}")
    print(f"confusion matrix:\n{cm}")
    print(f"\nfull report: \n{report}")

    with mlflow.start_run(run_name = "pretrained-evaluation"):
        mlflow.log_params({
            "model": "distilbert-base-uncased-finetuned-sst-2-english",
            "dataset": "amazon_polarity",
            "asin_evaluated": asin,
            "samples": len(rows),
            "fine-tuned": False,
        })
        mlflow.log_metrics({
            "accuracy": round(acc, 4),
            "f1_macro": round(f1, 4),
            "true_negatives": int(cm[0][0]),
            "false_positives": int(cm[0][1]),
            "false_negatives": int(cm[1][0]),
            "true_positives": int(cm[1][1]),
        })
        print("logged to mlflow!")

if __name__ == "__main__":
    evaluate_pretrained()