""" This file contains performs 3 main functions:
1. Preprocessing text, cleaning it to be ready for the model.
2. Loads 2000 samples of the Amazon Polarity dataset from Huggingface; drops short reviews; returns a compressed DataFrame with lesser columns
3. Starts a database session, and inserts the processed Product and Review data into their respective tables. Commits the changes if successful, or rolls back in case of failure.
"""

import re
import pandas as pd
from datasets import load_dataset
from pipeline.models import Review, Product, SessionLocal

def clean_text(text):
    """Cleans individual text samples.
    Returns: String"""
    text = text.lower() # convert text to lower-case for uniformity
    html_tags = r"<.*?>"
    special_chars = r"[^a-z0-9\s.,!?]" # anything that aren't letters, numbers, or certain chars
    whitespaces = r"\s+" # more than one blank space
    text = re.sub(html_tags, '', text)
    text = re.sub(special_chars, '', text)
    text = re.sub(whitespaces, ' ', text).strip()
    return text

def load_and_clean(no_samples):
    """Loads and Cleans dataset.
    Returns: pd.DataFrame"""
    dataset = load_dataset("amazon_polarity", split=f"train[:{no_samples}]")
    df = pd.DataFrame(dataset)
    df['clean_text'] = [clean_text(x) for x in df['content']] # using list comprehension to clean each sample
    df = df[df['clean_text'].str.len() > 20] # ignoring short reviews
    df = df.rename(columns = {
        'label': 'sentiment_label',
        'content': 'text'
    }) # renaming columns "label" and "content"
    return df[['title', 'text', 'clean_text', 'sentiment_label']]

def store_reviews(asin, reviews, db = None):
    """Stores processed reviews into database.
    Returns: Number of Reviews (count)"""
    close_after = False
    if db is None:
        db = SessionLocal()
        close_after = True
    
    try:
        product = db.query(Product).filter_by(asin = asin).first()
        if not product: # product doesn't exist yet
            product = Product(asin = asin)
            db.add(product)
            db.flush()
        
        count = 0
        for r in reviews:
            raw = r.get("text","") # empty string as a default
            clean = clean_text(raw)
            if not clean: # when clean_text returns nothing, i.e a skipped review
                continue
            review = Review( # creating Review object
                asin = asin,
                title = r.get("title",""),
                text = raw,
                clean_text = clean,
                rating = r.get("rating"),
            )
            db.add(review) # add review to session
            count += 1
        db.commit()
        print(f"stored {count} reviews for ASIN {asin}")
        return count
    
    except Exception as e:
        db.rollback() # revert to previous state if failure occurs
        print("error in storing reviews ",e)
        raise
    finally:
        if close_after:
            db.close()