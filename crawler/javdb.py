"""
JavDB 크롤러
- 배우 검색 → 배우 페이지 → 품번 목록 수집
- cloudscraper로 Cloudflare 우회
- 수집 결과는 SQLite DB에 저장
"""
import time
import re
import json
import logging
from typing import Optional, Generator
from urllib.parse import urljoin, urlencode, quote

import cloudscraper
from bs4 import BeautifulSoup

from .models import Actress, Video
from .db import get_conn, init_db, upsert_actress, upsert_video, link_actress_video

log = logging.getLogger(__name__)

BASE_URL = "https://javdb.com"
DELAY    = 1.5   # 요청 간격 (초)


# ── HTTP ──────────────────────────────────────────────────────────────────────

def _make_scraper():
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )
    scraper.headers.update({
        "Accept-Language": "ja,en;q=0.9",
        "Referer": BASE_URL,
    })
    return scraper


_scraper = None

def _get(url: str, params: dict = None) -> BeautifulSoup:
    global _scraper
    if _scraper is None:
        _scraper = _make_scraper()
    if params:
        url = url + "?" + urlencode(params, quote_via=quote)
    log.debug("GET %s", url)
    resp = _scraper.get(url, timeout=20)
    resp.raise_for_status()
    time.sleep(DELAY)
    return BeautifulSoup(resp.text, "html.parser")


# ── 배우 검색 ──────────────────────────────────────────────────────────────────

def search_actress(name: str) -> list[dict]:
    """
    배우 이름으로 검색. 결과 목록 반환.
    각 항목: {javdb_id, name, avatar_url, video_count}
    """
    soup = _get(f"{BASE_URL}/actors", {"q": name, "locale": "ja"})
    results = []

    for card in soup.select("div.actor-box"):
        a_tag = card.select_one("a")
        if not a_tag:
            continue
        href = a_tag.get("href", "")
        javdb_id = href.strip("/").split("/")[-1]

        img = card.select_one("img")
        avatar = img.get("src") or img.get("data-src") if img else None

        name_tag = card.select_one("strong") or card.select_one(".name")
        display_name = name_tag.get_text(strip=True) if name_tag else ""

        count_tag = card.select_one("span.tag") or card.select_one(".count")
        count_text = count_tag.get_text(strip=True) if count_tag else "0"
        video_count = int(re.sub(r"\D", "", count_text) or "0")

        results.append({
            "javdb_id": javdb_id,
            "name": display_name,
            "avatar_url": avatar,
            "video_count": video_count,
        })

    return results


# ── 배우 상세 페이지 ────────────────────────────────────────────────────────────

def _parse_actress_page(soup: BeautifulSoup, javdb_id: str) -> Actress:
    """배우 페이지 HTML → Actress 객체"""
    # 이름 파싱
    name_section = soup.select_one("section.actor-section") or soup.select_one(".actor-profile")
    names = []
    if name_section:
        for strong in name_section.select("strong"):
            t = strong.get_text(strip=True)
            if t:
                names.append(t)

    # 단순 title fallback
    if not names:
        title = soup.title.string if soup.title else ""
        names = [title.split("|")[0].strip()]

    # 일본어/영어 이름 분리
    name_ja, name_en = None, None
    primary_name = names[0] if names else javdb_id
    for n in names[1:]:
        if re.search(r'[ぁ-ん一-龯ァ-ン]', n):
            name_ja = n
        elif re.match(r'^[A-Za-z\s]+$', n):
            name_en = n

    # 아바타
    avatar_img = soup.select_one(".actor-avatar img") or soup.select_one("img.avatar")
    avatar_url = None
    if avatar_img:
        avatar_url = avatar_img.get("src") or avatar_img.get("data-src")

    return Actress(
        javdb_id=javdb_id,
        name=primary_name,
        name_ja=name_ja,
        name_en=name_en,
        aliases=names[1:],
        avatar_url=avatar_url,
    )


def _parse_video_cards(soup: BeautifulSoup) -> list[dict]:
    """페이지에서 영상 카드 목록 파싱"""
    videos = []
    for item in soup.select("div.item"):
        # 품번
        code_tag = item.select_one(".video-title strong") or item.select_one("strong")
        code = code_tag.get_text(strip=True) if code_tag else None
        if not code or not re.match(r'[A-Za-z]{2,8}-?\d{2,5}', code):
            continue

        # 제목
        title_tag = item.select_one(".video-title") or item.select_one("a")
        title = title_tag.get_text(strip=True) if title_tag else None

        # 날짜
        date_tag = item.select_one(".meta") or item.select_one(".date")
        release_date = None
        if date_tag:
            m = re.search(r'\d{4}-\d{2}-\d{2}', date_tag.get_text())
            if m:
                release_date = m.group()

        # 커버
        cover_img = item.select_one("img")
        cover_url = None
        if cover_img:
            cover_url = cover_img.get("src") or cover_img.get("data-src")

        # JavDB 슬러그
        a_tag = item.select_one("a")
        javdb_vid_id = None
        if a_tag:
            href = a_tag.get("href", "")
            javdb_vid_id = href.strip("/").split("/")[-1]

        videos.append({
            "code": code.upper(),
            "title": title,
            "release_date": release_date,
            "cover_url": cover_url,
            "javdb_id": javdb_vid_id,
        })
    return videos


def _next_page_url(soup: BeautifulSoup, current_url: str) -> Optional[str]:
    """다음 페이지 URL 추출"""
    next_a = soup.select_one("a.pagination-next") or soup.select_one("a[rel=next]")
    if next_a:
        href = next_a.get("href", "")
        if href:
            return urljoin(BASE_URL, href)
    return None


def fetch_actress_videos(
    javdb_id: str,
    max_pages: int = 10,
    progress_cb=None,
) -> Generator[dict, None, None]:
    """
    배우 ID로 전체 영상 목록 수집 (페이지네이션 처리).
    progress_cb(page, total_found) 콜백 선택.
    """
    url = f"{BASE_URL}/actors/{javdb_id}"
    page = 1
    total = 0

    while url and page <= max_pages:
        soup = _get(url)

        # 첫 페이지에서 배우 정보도 파싱
        if page == 1:
            yield {"_actress": _parse_actress_page(soup, javdb_id)}

        videos = _parse_video_cards(soup)
        total += len(videos)

        if progress_cb:
            progress_cb(page, total)

        for v in videos:
            yield v

        url = _next_page_url(soup, url)
        page += 1


# ── 통합 수집 + DB 저장 ────────────────────────────────────────────────────────

def crawl_and_save(
    name: str,
    max_pages: int = 10,
    progress_cb=None,
) -> dict:
    """
    배우 이름으로 검색 → 1위 배우의 전체 품번 수집 → DB 저장.
    반환: {actress: Actress, video_count: int, errors: list}
    """
    init_db()
    conn = get_conn()

    # 1. 검색
    results = search_actress(name)
    if not results:
        return {"actress": None, "video_count": 0, "errors": [f"'{name}' 검색 결과 없음"]}

    best = results[0]
    log.info("배우 발견: %s (javdb_id=%s, 작품 수~%d)", best["name"], best["javdb_id"], best["video_count"])

    # 2. 배우 페이지 크롤링
    actress_obj = None
    video_count = 0
    errors = []

    for item in fetch_actress_videos(best["javdb_id"], max_pages=max_pages, progress_cb=progress_cb):
        if "_actress" in item:
            actress_obj = item["_actress"]
            actress_id = upsert_actress(conn, actress_obj)
            actress_obj.db_id = actress_id
            continue

        try:
            video = Video(
                code=item["code"],
                title=item.get("title"),
                release_date=item.get("release_date"),
                cover_url=item.get("cover_url"),
                javdb_id=item.get("javdb_id"),
            )
            vid_id = upsert_video(conn, video)
            if actress_obj and actress_obj.db_id:
                link_actress_video(conn, actress_obj.db_id, vid_id)
            video_count += 1
        except Exception as e:
            errors.append(str(e))
            log.warning("영상 저장 실패: %s — %s", item.get("code"), e)

    conn.close()
    return {"actress": actress_obj, "video_count": video_count, "errors": errors}


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if len(sys.argv) < 2:
        print("사용법: python -m crawler.javdb <배우이름>")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    print(f"검색 중: {query}")

    def on_progress(page, total):
        print(f"  페이지 {page} 완료 — 누적 {total}개")

    result = crawl_and_save(query, max_pages=20, progress_cb=on_progress)

    if result["actress"]:
        a = result["actress"]
        print(f"\n배우: {a.name}")
        if a.name_ja:
            print(f"  일본어: {a.name_ja}")
        print(f"  저장된 품번: {result['video_count']}개")
    if result["errors"]:
        print(f"\n오류 {len(result['errors'])}건:")
        for e in result["errors"][:5]:
            print(f"  - {e}")
