"""
Collector Agent
RSS 피드, 뉴스 API, 직접 스크래핑으로 기사를 수집해서
data/raw/raw_YYYYMMDD.json 에 저장
"""

import json
import logging
import time
import hashlib
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import feedparser
import requests
from bs4 import BeautifulSoup

from config import (
    RAW_DIR, KEYWORDS_EN, KEYWORDS_KO,
    NEWSAPI_KEY, GUARDIAN_API_KEY, NYT_API_KEY, BRAVE_API_KEY,
    USER_AGENT, REQUEST_DELAY,
)
from feeds import ALL_FEEDS, CREDIBILITY
from sources import SCRAPE_SOURCES

logger = logging.getLogger(__name__)
HEADERS = {"User-Agent": USER_AGENT}


# ─────────────────────────────────────────────
# 유틸리티
# ─────────────────────────────────────────────

def make_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def is_iran_related(text: str) -> bool:
    text = text.lower()
    all_kw = KEYWORDS_EN + KEYWORDS_KO
    return any(kw.lower() in text for kw in all_kw)


def make_article(source, title, url, published="", summary="", credibility=7.0, lang="en"):
    return {
        "id":          make_id(url),
        "source":      source,
        "title":       title.strip(),
        "url":         url.strip(),
        "published":   published,
        "summary":     summary.strip()[:500],
        "credibility": credibility,
        "lang":        lang,
        "collected_at": datetime.utcnow().isoformat(),
    }


# ─────────────────────────────────────────────
# 1. RSS 피드 수집
# ─────────────────────────────────────────────

def collect_rss(feed_name: str, feed_url: str) -> list[dict]:
    articles = []
    try:
        resp = requests.get(feed_url, headers=HEADERS, timeout=10)
        feed = feedparser.parse(resp.text)
        cred = CREDIBILITY.get(feed_name, 7.5)

        for entry in feed.entries:
            title   = entry.get("title", "")
            link    = entry.get("link", "")
            summary = entry.get("summary", "") or entry.get("description", "")
            published = entry.get("published", "") or entry.get("updated", "")

            if not link:
                continue
            if not is_iran_related(title + " " + summary):
                continue

            articles.append(make_article(
                source=feed_name, title=title, url=link,
                published=published, summary=summary, credibility=cred,
            ))

        logger.info(f"[RSS] {feed_name}: {len(articles)}건 수집")
    except Exception as e:
        logger.warning(f"[RSS] {feed_name} 실패: {e}")
    return articles


def collect_all_rss() -> list[dict]:
    results = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {
            ex.submit(collect_rss, name, url): name
            for name, url in ALL_FEEDS.items()
        }
        for fut in as_completed(futures):
            results.extend(fut.result())
    logger.info(f"[RSS 전체] {len(results)}건")
    return results


# ─────────────────────────────────────────────
# 2. 뉴스 API 수집
# ─────────────────────────────────────────────

def collect_newsapi() -> list[dict]:
    if not NEWSAPI_KEY:
        logger.info("[NewsAPI] 키 없음, 건너뜀")
        return []
    articles = []
    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q":         " OR ".join(KEYWORDS_EN[:6]),
            "language":  "en",
            "sortBy":    "publishedAt",
            "pageSize":  100,
            "apiKey":    NEWSAPI_KEY,
        }
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()

        for item in data.get("articles", []):
            title   = item.get("title", "") or ""
            art_url = item.get("url", "")
            summary = item.get("description", "") or ""
            published = item.get("publishedAt", "")
            source  = item.get("source", {}).get("name", "NewsAPI")

            if not art_url or not is_iran_related(title + " " + summary):
                continue

            articles.append(make_article(
                source=f"NewsAPI:{source}", title=title, url=art_url,
                published=published, summary=summary, credibility=7.5,
            ))

        logger.info(f"[NewsAPI] {len(articles)}건 수집")
    except Exception as e:
        logger.warning(f"[NewsAPI] 실패: {e}")
    return articles


def collect_guardian_api() -> list[dict]:
    if not GUARDIAN_API_KEY:
        logger.info("[Guardian API] 키 없음, 건너뜀")
        return []
    articles = []
    try:
        url = "https://content.guardianapis.com/search"
        params = {
            "q":           "iran war",
            "section":     "world",
            "show-fields": "headline,bodyText,trailText",
            "order-by":    "newest",
            "page-size":   50,
            "api-key":     GUARDIAN_API_KEY,
        }
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()

        for item in data.get("response", {}).get("results", []):
            fields  = item.get("fields", {})
            title   = fields.get("headline", item.get("webTitle", ""))
            art_url = item.get("webUrl", "")
            summary = fields.get("trailText", "") or ""
            published = item.get("webPublicationDate", "")

            if not art_url:
                continue

            articles.append(make_article(
                source="Guardian_API", title=title, url=art_url,
                published=published, summary=summary, credibility=8.7,
            ))

        logger.info(f"[Guardian API] {len(articles)}건 수집")
    except Exception as e:
        logger.warning(f"[Guardian API] 실패: {e}")
    return articles


def collect_nyt_api() -> list[dict]:
    if not NYT_API_KEY:
        logger.info("[NYT API] 키 없음, 건너뜀")
        return []
    articles = []
    try:
        today = date.today().strftime("%Y%m%d")
        url = "https://api.nytimes.com/svc/search/v2/articlesearch.json"
        params = {
            "q":          "iran war",
            "fq":         'news_desk:("Foreign" "World" "International")',
            "sort":       "newest",
            "begin_date": today,
            "api-key":    NYT_API_KEY,
        }
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()

        for item in data.get("response", {}).get("docs", []):
            title   = item.get("headline", {}).get("main", "")
            art_url = item.get("web_url", "")
            summary = item.get("abstract", "") or item.get("snippet", "")
            published = item.get("pub_date", "")

            if not art_url or not is_iran_related(title + " " + summary):
                continue

            articles.append(make_article(
                source="NYT_API", title=title, url=art_url,
                published=published, summary=summary, credibility=8.8,
            ))

        logger.info(f"[NYT API] {len(articles)}건 수집")
    except Exception as e:
        logger.warning(f"[NYT API] 실패: {e}")
    return articles


def collect_brave_api() -> list[dict]:
    if not BRAVE_API_KEY:
        logger.info("[Brave API] 키 없음, 건너뜀")
        return []
    articles = []
    try:
        url = "https://api.search.brave.com/res/v1/news/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": BRAVE_API_KEY,
        }
        params = {"q": "iran war hormuz blockade", "count": 20, "freshness": "pd"}
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        data = resp.json()

        for item in data.get("results", []):
            title   = item.get("title", "")
            art_url = item.get("url", "")
            summary = item.get("description", "")
            published = item.get("age", "")
            source  = item.get("source", {}).get("name", "Brave")

            if not art_url or not is_iran_related(title + " " + summary):
                continue

            articles.append(make_article(
                source=f"Brave:{source}", title=title, url=art_url,
                published=published, summary=summary, credibility=7.5,
            ))

        logger.info(f"[Brave API] {len(articles)}건 수집")
    except Exception as e:
        logger.warning(f"[Brave API] 실패: {e}")
    return articles


# ─────────────────────────────────────────────
# 3. 직접 스크래핑
# ─────────────────────────────────────────────

def scrape_site(site_name: str, cfg: dict) -> list[dict]:
    articles = []
    try:
        resp = requests.get(cfg["url"], headers=HEADERS, timeout=12)
        soup = BeautifulSoup(resp.text, "html.parser")

        tags = soup.select(cfg["title_sel"])[:15]
        for tag in tags:
            title = tag.get_text(strip=True)
            href  = tag.get("href", "")

            if not href:
                continue
            if not href.startswith("http"):
                href = cfg.get("base_url", "") + href

            # 날짜 추출 시도
            published = ""
            date_tags = soup.select(cfg.get("date_sel", "time"))
            if date_tags:
                published = date_tags[0].get("datetime", "") or date_tags[0].get_text(strip=True)

            if not is_iran_related(title):
                continue

            articles.append(make_article(
                source=site_name, title=title, url=href,
                published=published, credibility=cfg.get("credibility", 8.0),
            ))

        time.sleep(REQUEST_DELAY)
        logger.info(f"[Scrape] {site_name}: {len(articles)}건 수집")
    except Exception as e:
        logger.warning(f"[Scrape] {site_name} 실패: {e}")
    return articles


def collect_all_scrape() -> list[dict]:
    results = []
    today_weekday = datetime.today().weekday()  # 0=월 6=일

    for name, cfg in SCRAPE_SOURCES.items():
        schedule = cfg.get("schedule", "daily")
        # weekly 소스는 월요일(0)에만 수집
        if schedule == "weekly" and today_weekday != 0:
            continue
        results.extend(scrape_site(name, cfg))

    logger.info(f"[Scrape 전체] {len(results)}건")
    return results


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────

def run(target_date: str = None) -> Path:
    if target_date is None:
        target_date = date.today().strftime("%Y-%m-%d")

    logger.info(f"=== Collector 시작: {target_date} ===")

    # 병렬 수집
    all_articles = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = [
            ex.submit(collect_all_rss),
            ex.submit(collect_newsapi),
            ex.submit(collect_guardian_api),
            ex.submit(collect_nyt_api),
            ex.submit(collect_brave_api),
            ex.submit(collect_all_scrape),
        ]
        for fut in as_completed(futures):
            all_articles.extend(fut.result())

    # 저장
    out_path = RAW_DIR / f"raw_{target_date.replace('-', '')}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)

    logger.info(f"=== Collector 완료: {len(all_articles)}건 → {out_path} ===")
    return out_path


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    d = sys.argv[1] if len(sys.argv) > 1 else None
    run(d)
