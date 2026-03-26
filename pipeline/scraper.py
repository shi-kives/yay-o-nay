import re, time, random, requests
from bs4 import BeautifulSoup

HEADERS_LIST = [
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36", "Accept-Language": "en-US,en;q=0.9", "Referer": "https://www.amazon.com/"},
    {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36", "Accept-Language": "en-US,en;q=0.9", "Referer": "https://www.amazon.com/"},
]

def extract_asin(url):
    match = re.search(r'/(?:dp|gp/product|product)/([A-Z0-9]{10})', url)
    if not match:
        raise ValueError(f"couldn't find asin in {url}")
    return match.group(1)

def scrape_reviews(asin, max_pages = 5):
    reviews = []
    for page in range(1, max_pages + 1):
        url = f"https://www.amazon.com/product-reviews/{asin}?pageNumber={page}&sortBy=recent"
        headers = random.choice(HEADERS_LIST)

        try:
            resp = requests.get(url, headers=headers, timeout=10)
        except requests.RequestException:
            break

        if resp.status_code != 200:
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        review_divs = soup.find_all("span", {"data-hook": "review-body"})
        rating_spans = soup.find_all("i", {"data-hook": "review-star-rating"})
        title_anchors = soup.find_all("a", {"data-hook": "review-title"})

        if not review_divs:
            break

        for i, div in enumerate(review_divs):
            rating_text = rating_spans[i].text.strip() if i < len(rating_spans) else ""
            rating_match = re.search(r'[\d.]+', rating_text)
            reviews.append({
                "text": div.get_text(strip=True),
                "rating": float(rating_match.group()) if rating_match else None,
                "title": title_anchors[i].get_text(strip=True) if i < len(title_anchors) else ""
            })
        time.sleep(random.uniform(2,5))
    return reviews
