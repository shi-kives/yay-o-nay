from pipeline.models import create_tables
from pipeline.ingest import load_and_clean, store_reviews

def seed_db():
    print("creating tables in case they don't exist")
    create_tables()

    num_samples = 2000
    print("loading and cleaning dataset")
    df = load_and_clean(num_samples)

    # the reviews in the Polarity Dataset belong to fake products without ASINs, so we divide 2000 samples into 4 products, each with 500 reviews, and 4 different fake ASINs
    chunk_size = num_samples // 4
    fake_asins = ["B000000001","B000000002","B000000003","B000000004"]

    for i, asin in enumerate(fake_asins):
        chunk = df.iloc[i * chunk_size : (i + 1) * chunk_size] # create a "chunk" of reviews from the ranges 0-500, 500-1000, 1000-1500, 1500-2000
        reviews = chunk.to_dict(orient = "records") # converting the DataFrame object "chunk" into a dict
        for r in reviews:
            r["rating"] = 5.0 if r["sentiment_label"] == 1 else 1.0 # rating = 5.0 if sentiment_label = 1, otherwise rating = 1.0
        store_reviews(asin, reviews)

    print("seed complete. run 'select count(*) from reviews;' in postgres to verify.")

if __name__ == "__main__":
    seed_db()