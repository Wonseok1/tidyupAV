import requests
from bs4 import BeautifulSoup
import cloudscraper

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def fetch_html(url):
    scraper = cloudscraper.create_scraper()
    res = scraper.get(url)
    return res.text

def extract_items(html):
    soup = BeautifulSoup(html, "html.parser")

    items = []

    # ⚠️ 사이트 구조에 맞게 수정 필요
    for a in soup.select("a"):
        text = a.get_text(strip=True)

        # 품번 형태만 필터
        if "-" in text and len(text) < 20:
            items.append(text)

    return items