from sqlalchemy import (Column, Integer, String, Float, DateTime, Text, ForeignKey, create_engine)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key = True, index = True)
    asin = Column(String(10), unique = True, nullable = False, index = True)
    name = Column(String(500), nullable = True)
    scraped_at = Column(DateTime, default=datetime.now)
    reviews = relationship("Review", back_populates="product")

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key = True, index = True)
    asin = Column(String(10), ForeignKey("products.asin"), nullable = False, index = True)
    title = Column(String(500), nullable = True)
    text = Column(Text, nullable = False)
    clean_text = Column(Text, nullable = False)
    rating = Column(Float, nullable = True)
    created_at = Column(DateTime, default = datetime.now())

    product = relationship("Product", back_populates="reviews")
    prediction = relationship("Prediction", back_populates = "review", uselist = False)
    aspects = relationship("AspectSentiment", back_populates = "review")

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key = True, index = True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable = False, unique = True)
    sentiment_label = Column(String(10), nullable = False)
    score = Column(Float, nullable = False)
    created_at = Column(DateTime, default = datetime.now)

    review = relationship("Review", back_populates = "prediction")

class AspectSentiment(Base):
    __tablename__ = "aspect_sentiments"
    
    id = Column(Integer, primary_key = True, index = True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable = False)
    asin = Column(String(10), nullable = False, index = True)
    aspect = Column(String(100), nullable = False) # features of the product
    opinion = Column(String(100), nullable = True)
    vader_score = Column(Float, nullable = False)

    review = relationship("Review", back_populates = "aspects")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/yayonay")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit = False, autoflush = False, bind = engine) # commits are manual

def create_tables():
    Base.metadata.create_all(bind = engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()