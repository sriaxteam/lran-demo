"""
International Organization Collector
국제기구 공식 발표 수집 — IEA · IMF · OECD · 세계은행 · UNCTAD · OPEC

수집 대상:
  - IEA: Oil Market Report, 에너지 안보 성명, IEA-IMF-WB 공동 성명
  - IMF: World Economic Outlook, 긴급 성명, 국가별 전망
  - OECD: Economic Outlook, 인플레이션 모니터, 국가별 경제 보고서
  - World Bank: Global Economic Prospects, 취약국 지원 성명
  - UNCTAD: Transport Review, 무역 동향
  - OPEC: Monthly Oil Market Report, 생산량 결정문

출력: data/intl/intl_YYYYMMDD.json
"""

import json
import logging
import time
import hashlib
from datetime import date, datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import feedparser
import requests
from bs4 import BeautifulSoup

from config import DATA_DIR, KEYWORDS_EN, USER_AGENT, REQUEST_DELAY

logger = logging.getLogger(__name__)
HEADERS = {"User-Agent": USER_AGENT}

INTL_DIR = DATA_DIR / "intl"
INTL_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────
# 소스 정의
# ─────────────────────────────────────────────

# RSS 피드 (무료, API 키 불필요)
# Google News RSS 우회 수집 (직접 RSS 403/404 차단 대응)
_GN = "https://news.google.com/rss/search?hl=en&gl=US&ceid=US:en&q="

INTL_RSS_FEEDS = {
    "IEA_News": {
        "url":         f"{_GN}site:iea.org+energy",
        "credibility": 9.8,
        "org_type":    "국제기구",
        "focus":       "에너지안보·유가·비축유",
        "paradigm_weight": 5,
    },
    "IMF_News": {
        "url":         f"{_GN}site:imf.org",
        "credibility": 9.8,
        "org_type":    "국제기구",
        "focus":       "세계경제전망·물가·성장",
        "paradigm_weight": 5,
    },
    "OECD_News": {
        "url":         f"{_GN}site:oecd.org+economy",
        "credibility": 9.7,
        "org_type":    "국제기구",
        "focus":       "선진국경제·인플레이션·정책",
        "paradigm_weight": 4,
    },
    "WorldBank_News": {
        "url":         f"{_GN}site:worldbank.org",
        "credibility": 9.7,
        "org_type":    "국제기구",
        "focus":       "개발경제·취약국·식량안보",
        "paradigm_weight": 4,
    },
    "UNCTAD_News": {
        "url":         f"{_GN}site:unctad.org+trade",
        "credibility": 9.5,
        "org_type":    "국제기구",
        "focus":       "무역·공급망·해운패러다임",
        "paradigm_weight": 4,
    },
    "OPEC_News": {
        "url":         f"{_GN}site:opec.org+oil",
        "credibility": 9.5,
        "org_type":    "국제기구",
        "focus":       "산유량·유가·OPEC+결정",
        "paradigm_weight": 3,
    },
}

# 스크래핑 대상 (RSS 미지원 또는 핵심 문서 직접 수집)
INTL_SCRAPE_TARGETS = {
    "IEA_Reports": {
        "url":         "https://www.iea.org/topics/oil-markets",
        "title_sel":   "h3 a, h4 a, .m-article-card__heading a",
        "date_sel":    "time",
        "base_url":    "https://www.iea.org",
        "credibility": 9.8,
        "org_type":    "국제기구",
        "focus":       "Oil Market Report·에너지안보보고서",
        "paradigm_weight": 5,
    },
    "IMF_WEO": {
        "url":         "https://www.imf.org/en/Publications/WEO",
        "title_sel":   "h3 a, h2 a, .search-result-item a",
        "date_sel":    "time, .date",
        "base_url":    "https://www.imf.org",
        "credibility": 9.8,
        "org_type":    "국제기구",
        "focus":       "World Economic Outlook·분기 경제 전망",
        "paradigm_weight": 5,
    },
    "OPEC_Reports": {
        "url":         "https://www.opec.org/opec_web/en/publications/338.htm",
        "title_sel":   "a.reports-link, h3 a",
        "date_sel":    "span.date",
        "base_url":    "https://www.opec.org",
        "credibility": 9.5,
        "org_type":    "국제기구",
        "focus":       "Monthly Oil Market Report",
        "paradigm_weight": 3,
    },
}

# 패러다임 변화 감지 키워드 (일반 이란 키워드와 별도)
PARADIGM_KEYWORDS = [
    # 에너지 안보 재편
    "energy security", "energy transition", "energy partnership",
    "reliability", "supply diversification", "strategic reserve",
    "oil market", "hormuz", "energy crisis", "largest energy",
    # 경제 구조 변화
    "recession", "growth forecast", "inflation outlook", "gdp",
    "global economy", "economic outlook", "downgrade", "slowdown",
    "trade disruption", "supply chain", "shipping route",
    # 정책 패러다임
    "hoarding", "export controls", "price cap", "emergency",
    "coordination group", "joint statement", "paradigm",
    "fragmentation", "geopolitical", "decoupling",
]


# ─────────────────────────────────────────────
# 유틸리티
# ─────────────────────────────────────────────

def make_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def is_relevant(text: str) -> bool:
    """이란전쟁 또는 패러다임 변화 관련 여부 확인"""
    text = text.lower()
    iran_match = any(kw.lower() in text for kw in KEYWORDS_EN)
    paradigm_match = any(kw.lower() in text for kw in PARADIGM_KEYWORDS)
    return iran_match or paradigm_match


def detect_paradigm_signals(text: str) -> list:
    """패러다임 변화 신호 키워드 목록 반환"""
    text = text.lower()
    return [kw for kw in PARADIGM_KEYWORDS if kw.lower() in text]


def make_article(source, title, url, published="", summary="",
                 credibility=9.0, org_type="국제기구",
                 focus="", paradigm_weight=3):
    signals = detect_paradigm_signals(title + " " + summary)
    return {
        "id":               make_id(url),
        "source":           source,
        "title":            title.strip(),
        "url":              url.strip(),
        "published":        published,
        "summary":          summary.strip()[:600],
        "credibility":      credibility,
        "org_type":         org_type,
        "focus":            focus,
        "paradigm_weight":  paradigm_weight,
        "paradigm_signals": signals,
        "is_paradigm_item": len(signals) >= 2,
        "collected_at":     datetime.utcnow().isoformat(),
        "data_type":        "intl_org",
    }


# ─────────────────────────────────────────────
# 1. RSS 수집
# ─────────────────────────────────────────────

def collect_rss(source_name: str, cfg: dict) -> list:
    """국제기구는 키워드 필터 없이 전량 수집 — 간접 영향 분석에 모두 유용"""
    articles = []
    try:
        resp = requests.get(cfg["url"], headers=HEADERS, timeout=12)
        feed = feedparser.parse(resp.text)

        for entry in feed.entries:
            title   = entry.get("title", "")
            link    = entry.get("link", "")
            summary = entry.get("summary", "") or entry.get("description", "")
            pub     = entry.get("published", "") or entry.get("updated", "")

            if not link or not title:
                continue
            # 키워드 필터 제거 — 국제기구 발표는 이란 미언급이어도 패러다임·경제 분석에 활용

            articles.append(make_article(
                source=source_name,
                title=title, url=link,
                published=pub, summary=summary,
                credibility=cfg["credibility"],
                org_type=cfg["org_type"],
                focus=cfg["focus"],
                paradigm_weight=cfg["paradigm_weight"],
            ))

        logger.info(f"[RSS·{source_name}] {len(articles)}건")
    except Exception as e:
        logger.warning(f"[RSS·{source_name}] 실패: {e}")
    return articles


# ─────────────────────────────────────────────
# 2. 스크래핑
# ─────────────────────────────────────────────

def scrape_target(source_name: str, cfg: dict) -> list:
    """국제기구 보고서 스크래핑 — 키워드 필터 없이 전량 수집"""
    articles = []
    try:
        resp = requests.get(cfg["url"], headers=HEADERS, timeout=14)
        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup.select(cfg["title_sel"])[:12]:
            title = tag.get_text(strip=True)
            href  = tag.get("href", "")

            if not href or not title:
                continue
            if not href.startswith("http"):
                href = cfg.get("base_url", "") + href

            # 날짜 추출
            published = ""
            dt = soup.select_one(cfg.get("date_sel", "time"))
            if dt:
                published = dt.get("datetime", "") or dt.get_text(strip=True)

            # 키워드 필터 제거 — 국제기구 보고서는 전량 수집

            articles.append(make_article(
                source=source_name,
                title=title, url=href,
                published=published,
                credibility=cfg["credibility"],
                org_type=cfg["org_type"],
                focus=cfg["focus"],
                paradigm_weight=cfg["paradigm_weight"],
            ))

        time.sleep(REQUEST_DELAY)
        logger.info(f"[Scrape·{source_name}] {len(articles)}건")
    except Exception as e:
        logger.warning(f"[Scrape·{source_name}] 실패: {e}")
    return articles


# ─────────────────────────────────────────────
# 3. 메인
# ─────────────────────────────────────────────

def run(target_date: str = None) -> Path:
    if target_date is None:
        target_date = date.today().strftime("%Y-%m-%d")

    logger.info(f"=== IntlOrgCollector 시작: {target_date} ===")

    all_articles = []

    # RSS 병렬 수집
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {
            ex.submit(collect_rss, name, cfg): name
            for name, cfg in INTL_RSS_FEEDS.items()
        }
        for fut in as_completed(futures):
            all_articles.extend(fut.result())

    # 스크래핑 순차 실행 (서버 부하 방지)
    for name, cfg in INTL_SCRAPE_TARGETS.items():
        all_articles.extend(scrape_target(name, cfg))

    # 패러다임 아이템 통계
    paradigm_items = [a for a in all_articles if a["is_paradigm_item"]]
    logger.info(f"패러다임 변화 신호 포함 기사: {len(paradigm_items)}건")

    # 저장
    date_str = target_date.replace("-", "")
    out_path = INTL_DIR / f"intl_{date_str}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)

    logger.info(f"=== IntlOrgCollector 완료: {len(all_articles)}건 → {out_path} ===")
    return out_path


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    d = sys.argv[1] if len(sys.argv) > 1 else None
    run(d)
