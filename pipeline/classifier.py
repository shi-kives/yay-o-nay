import torch
from transformers import pipeline
from sqlalchemy.orm import Session
from pipeline.models import Review, Prediction

# pipeline here wraps tokenizer, model and softmax into one callable object

_classifier = pipeline(
    "sentiment-analysis",
    model = "distilbert-base-uncased-finetuned-sst-2-english",
    device = -1, # change this to 0 if you have a GPU
    truncation = True,
    max_length = 512
)

def classify(text):
    if not text or not text.strip():
        return {"label": "NEGATIVE", "score": 0.5}
    result = _classifier(text)[0] # run the model 
    return {"label": result["label"], "score": round(result["score"], 4)}

def batch_inference(asin, db):

    unclassified = (
        db.query(Review).filter(Review.asin == asin).outerjoin(Prediction, Prediction.review_id == Review.id).filter(Prediction.id == None).all()
    ) # creating a list of all reviews without a prediction

    if not unclassified: # no reviews w/o prediction
        print(f"no unclassified reviews for {asin}")
        return 0
    
    print(f"classifying {len(unclassified)} reviews for {asin} ... ...")

    BATCH_SIZE = 32 # feel free to increase it to 64 if a GPU is present
    count = 0

    for i in range(0, len(unclassified), BATCH_SIZE):
        batch = unclassified[i : i + BATCH_SIZE] # create a list of reviews w/o predictions from the ranges 0-31, 32-63 and so on.
        texts = [r.clean_text for r in batch] # create a list of the cleaned reviews

        results = _classifier(texts)

        for review, result in zip(batch, results):
            prediction = Prediction(
                review_id = review.id,
                sentiment_label = result["label"],
                score = round(result["score"], 4)
            ) # create an entry in the prediction table
            db.add(prediction)
            count += 1
        
        db.commit()
        print(f"batch {i//BATCH_SIZE + 1} done -- {count} reviews predicted so far.")
    
    return count
