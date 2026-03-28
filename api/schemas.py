from pydantic import BaseModel, HttpUrl
from typing import Optional, List

class UrlRequest(BaseModel):
    url: str

class TextRequest(BaseModel):
    text: str

class SentimentOut(BaseModel):
    label: str
    score: float

class ProductScore(BaseModel):
    asin: str
    score: float
    confidence: float
    review_count: int

class Recommendation(BaseModel):
    verdict: str
    label: str
    score: float
    reason: str
    confidence: float
    positives: List[str]
    negatives: List[str]

class TrendPoint(BaseModel):
    week: str
    avg_score: float
    is_anomaly: bool

class CompareResult(BaseModel):
    asin_a: str
    asin_b: str
    similarity: float

class TaskStatus(BaseModel):
    task_id: str
    status: str
    info: Optional[dict] = None
    result: Optional[dict] = None