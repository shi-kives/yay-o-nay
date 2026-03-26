import re, time, random
from bs4 import BeautifulSoup
from selenium import webdriver 
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

HEADERS_LIST = [
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36", "Accept-Language": "en-US,en;q=0.9", "Referer": "https://www.amazon.in/"},
    {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36", "Accept-Language": "en-US,en;q=0.9", "Referer": "https://www.amazon.in/"},
]

def extract_asin(url):
    match = re.search(r'/(?:dp|gp/product|product)/([A-Z0-9]{10})', url)
    if not match:
        raise ValueError(f"couldn't find asin in {url}")
    return match.group(1)

def scrape_reviews(asin, max_pages = 5):
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    reviews = []

    for page in range(1, max_pages + 1):
        url = f"https://www.amazon.in/product-reviews/{asin}?pageNumber={page}&sortBy=recent"
        driver.get(url)
        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        review_divs = soup.select("span.review-text-content span")
        rating_spans = soup.select("i.review-rating span")
        title_anchors = soup.select("a.review-title span")

        if not review_divs:
            print("can't find review divs (most likely blocked)")
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
    driver.quit()
    return reviews
