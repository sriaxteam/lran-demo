"""
Korea Research & Global Think-Tank Collector
한국 국책연구기관 + 국외 싱크탱크·정부 수집

한국 연구기관:
  - KEEI (한국에너지경제연구원): 에너지 이슈 브리핑, 이란전쟁 영향 보고서
  - KIEP (대외경제정책연구원): 대외경제 파급 효과, 공급망 분석
  - KDI (한국개발연구원): 거시경제, 물가, 고용 영향 분석

국외 싱크탱크·정부:
  - Chatham House: 중동 질서 재편, 에너지 안보 장기 시나리오
  - EU 집행위원회: EU 에너지·민생 공동 대응 정책
  - 일본 METI: 에너지 보조금, LNG 확보 정책 벤치마킹

출력: data/research/research_YYYYMMDD.json
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

from config import DATA_DIR, USER_AGENT, REQUEST_DELAY

logger = logging.getLogger(__name__)
HEADERS = {"User-Agent": USER_AGENT}

RESEARCH_DIR = DATA_DIR / "research"
RESEARCH_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────
# 소스 정의
# ─────────────────────────────────────────────

RESEARCH_RSS = {
    # ── 한국 국책연구기관
    "KEEI": {
        "url":         "https://www.keei.re.kr/keei/rss/newsRss.rss",
        "credibility": 9.0,
        "country":     "한국",
        "org_type":    "국책연구원",
        "focus":       "에너지정책·이란전쟁한국영향",
        "lang":        "ko",
        "suwon_relevance": "수원시 에너지비 분석·보고서 인용 핵심",
        "keywords_ko": [
            # 이란 직접
            "이란", "호르무즈", "테헤란", "이란전", "이란 핵",
            # 중동 지역
            "중동", "중동전쟁", "페르시아만", "홍해", "후티", "헤즈볼라",
            # 에너지·유가
            "에너지", "유가", "원유", "LNG", "에너지안보", "에너지 위기",
            "유류비", "난방비", "도시가스", "전기료",
            # 경제·공급망
            "물가", "인플레", "공급망", "해운 운임",
        ],
        "keywords_en": ["iran", "hormuz", "energy", "oil", "lng", "energy security"],
    },
    "KIEP": {
        "url":         "https://www.kiep.go.kr/rss/rssFeed.do",
        "credibility": 9.0,
        "country":     "한국",
        "org_type":    "국책연구원",
        "focus":       "대외경제파급·공급망·무역",
        "lang":        "ko",
        "suwon_relevance": "수원시 수출기업·공급망 영향 논거",
        "keywords_ko": [
            # 이란 직접
            "이란", "호르무즈", "이란전", "이란 봉쇄",
            # 중동 지역
            "중동", "중동전쟁", "페르시아만", "홍해", "후티",
            "가자", "하마스", "이스라엘",
            # 에너지·유가
            "에너지", "원유", "LNG", "유가",
            # 경제·공급망
            "공급망", "무역", "수출", "수입", "물가", "인플레",
            "해운 운임", "공급망 재편", "경제 제재",
        ],
        "keywords_en": [
            "iran", "hormuz", "middle east", "oil", "supply chain",
            "trade", "sanction", "shipping", "inflation",
        ],
    },
    "KDI": {
        "url":         "https://www.kdi.re.kr/common/rss.jsp",
        "credibility": 9.0,
        "country":     "한국",
        "org_type":    "국책연구원",
        "focus":       "거시경제·물가·고용영향",
        "lang":        "ko",
        "suwon_relevance": "수원시 민생물가·고용 분석 국내 기준",
        "keywords_ko": [
            # 이란 직접
            "이란", "호르무즈", "이란전",
            # 중동 지역
            "중동", "중동전쟁", "홍해", "후티",
            # 에너지·유가
            "에너지", "유가", "원유", "LNG", "에너지 위기",
            "유류비", "난방비", "전기료",
            # 경제·민생
            "물가", "인플레이션", "인플레", "고용", "경기", "성장",
            "소비", "소상공인", "민생", "가계", "생활비",
            "공급망", "해운 운임",
        ],
        "keywords_en": [
            "iran", "oil price", "energy", "inflation",
            "supply chain", "middle east", "recession",
        ],
    },

    # ── 국외 싱크탱크·정부
    "ChathamHouse": {
        "url":         "https://www.chathamhouse.org/rss.xml",
        "credibility": 9.0,
        "country":     "영국",
        "org_type":    "싱크탱크",
        "focus":       "중동질서재편·에너지안보장기시나리오",
        "lang":        "en",
        "suwon_relevance": "수원시 보고서 국제 논거·패러다임 분석",
        "keywords_ko": [],
        "keywords_en": [
            "iran", "hormuz", "energy", "middle east", "oil", "paradigm",
            "geopolitics", "energy security", "persian gulf", "red sea",
            "houthi", "hezbollah", "israel", "gaza", "hamas",
            "oil price", "crude oil", "supply chain", "sanction",
            "inflation", "shipping", "tanker",
        ],
    },
    "EU_Commission": {
        "url":         "https://ec.europa.eu/rss/energy_en.xml",
        "credibility": 9.0,
        "country":     "EU",
        "org_type":    "정부/국제기구",
        "focus":       "EU에너지·민생공동대응정책",
        "lang":        "en",
        "suwon_relevance": "에너지 가격 상한제·취약계층 바우처 벤치마킹",
        "keywords_ko": [],
        "keywords_en": [
            "energy", "gas", "oil", "inflation", "price", "iran",
            "supply", "security", "consumer", "household",
            "energy crisis", "lng", "energy security", "middle east",
            "red sea", "supply chain", "fuel", "heating",
        ],
    },
}

# 스크래핑 대상 (RSS 미지원 또는 핵심 페이지 직접 수집)
RESEARCH_SCRAPE = {
    "KEEI_Reports": {
        "url":         "https://www.keei.re.kr/keei/portal/bbs/list.do?bbsId=BBSMSTR_000000000060",
        "title_sel":   "td.title a, .bbs-list td a",
        "date_sel":    "td.date, .bbs-date",
        "base_url":    "https://www.keei.re.kr",
        "credibility": 9.0,
        "country":     "한국",
        "org_type":    "국책연구원",
        "focus":       "에너지이슈브리핑·보고서",
        "lang":        "ko",
        "suwon_relevance": "에너지 정책 분석 수원시 직접 인용 가능",
        "keywords_ko": [
            "이란", "에너지", "유가", "원유", "LNG", "호르무즈",
            "에너지안보", "에너지 위기", "중동", "홍해", "유류비",
            "난방비", "전기료", "도시가스", "물가", "공급망",
        ],
        "keywords_en": ["iran", "energy", "oil", "lng", "hormuz", "middle east"],
    },
    "KIEP_Reports": {
        "url":         "https://www.kiep.go.kr/gallery.es?mid=a10100000000&bid=0001",
        "title_sel":   "td.title a, .data-list td a",
        "date_sel":    "td.date",
        "base_url":    "https://www.kiep.go.kr",
        "credibility": 9.0,
        "country":     "한국",
        "org_type":    "국책연구원",
        "focus":       "세계경제포커스·오늘의세계경제",
        "lang":        "ko",
        "suwon_relevance": "대외경제 파급 효과 공식 논거",
        "keywords_ko": [
            "이란", "에너지", "원유", "공급망", "무역", "물가",
            "호르무즈", "중동", "홍해", "인플레", "수출", "수입",
            "해운", "제재", "이스라엘", "가자", "후티",
        ],
        "keywords_en": [
            "iran", "oil", "energy", "supply chain", "trade",
            "middle east", "sanction", "inflation", "hormuz",
        ],
    },
    "METI_Japan": {
        "url":         "https://www.meti.go.jp/press/index_en.html",
        "title_sel":   "div.list-title a, .press-list a",
        "date_sel":    "span.date, .press-date",
        "base_url":    "https://www.meti.go.jp",
        "credibility": 9.0,
        "country":     "일본",
        "org_type":    "정부부처",
        "focus":       "일본에너지보조금·LNG정책벤치마킹",
        "lang":        "en",
        "suwon_relevance": "에너지 가격 보조금 직접 지급·LNG 확보 전략 벤치마킹",
        "keywords_ko": [],
        "keywords_en": [
            "energy", "lng", "oil", "gas", "subsidy", "price",
            "iran", "hormuz", "fuel", "electricity",
            "energy security", "crude oil", "middle east",
            "supply", "import", "inflation",
        ],
    },
    "EU_Energy_Policy": {
        "url":         "https://energy.ec.europa.eu/news_en",
        "title_sel":   "article h3 a, .ecl-content-item__title a",
        "date_sel":    "time",
        "base_url":    "https://energy.ec.europa.eu",
        "credibility": 9.0,
        "country":     "EU",
        "org_type":    "정부/국제기구",
        "focus":       "EU에너지정책·취약계층지원",
        "lang":        "en",
        "suwon_relevance": "유럽 에너지 바우처·가격 상한제 수원시 벤치마킹",
        "keywords_ko": [],
        "keywords_en": [
            "energy", "gas", "oil", "iran", "price", "consumer",
            "vulnerable", "household", "security",
            "energy crisis", "lng", "heating", "fuel", "electricity",
            "red sea", "supply chain", "middle east", "inflation",
        ],
    },
}


# ─────────────────────────────────────────────
# 유틸리티
# ─────────────────────────────────────────────

def make_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def is_relevant(text: str, keywords_ko: list, keywords_en: list) -> bool:
    text_lower = text.lower()
    return (
        any(kw in text for kw in keywords_ko) or
        any(kw.lower() in text_lower for kw in keywords_en)
    )


def make_article(source, title, url, published="", summary="",
                 credibility=9.0, country="", org_type="",
                 focus="", lang="ko", suwon_relevance=""):
    return {
        "id":               make_id(url),
        "source":           source,
        "title":            title.strip(),
        "url":              url.strip(),
        "published":        published,
        "summary":          summary.strip()[:600],
        "credibility":      credibility,
        "country":          country,
        "org_type":         org_type,
        "focus":            focus,
        "lang":             lang,
        "suwon_relevance":  suwon_relevance,
        "collected_at":     datetime.utcnow().isoformat(),
        "data_type":        "research",
    }


# ─────────────────────────────────────────────
# 1. RSS 수집
# ─────────────────────────────────────────────

def collect_rss(source_name: str, cfg: dict) -> list:
    articles = []
    try:
        resp = requests.get(cfg["url"], headers=HEADERS, timeout=12)
        feed = feedparser.parse(resp.text)

        for entry in feed.entries:
            title   = entry.get("title", "")
            link    = entry.get("link", "")
            summary = entry.get("summary", "") or entry.get("description", "")
            pub     = entry.get("published", "") or entry.get("updated", "")

            if not link:
                continue
            if not is_relevant(
                title + " " + summary,
                cfg["keywords_ko"],
                cfg["keywords_en"]
            ):
                continue

            articles.append(make_article(
                source=source_name, title=title, url=link,
                published=pub, summary=summary,
                credibility=cfg["credibility"],
                country=cfg["country"],
                org_type=cfg["org_type"],
                focus=cfg["focus"],
                lang=cfg["lang"],
                suwon_relevance=cfg["suwon_relevance"],
            ))

        logger.info(f"[RSS·{source_name}] {len(articles)}건")
    except Exception as e:
        logger.warning(f"[RSS·{source_name}] 실패: {e}")
    return articles


# ─────────────────────────────────────────────
# 2. 스크래핑
# ─────────────────────────────────────────────

def scrape_target(source_name: str, cfg: dict) -> list:
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

            if not is_relevant(title, cfg["keywords_ko"], cfg["keywords_en"]):
                continue

            published = ""
            dt = soup.select_one(cfg.get("date_sel", "time"))
            if dt:
                published = dt.get("datetime", "") or dt.get_text(strip=True)

            articles.append(make_article(
                source=source_name, title=title, url=href,
                published=published,
                credibility=cfg["credibility"],
                country=cfg["country"],
                org_type=cfg["org_type"],
                focus=cfg["focus"],
                lang=cfg["lang"],
                suwon_relevance=cfg["suwon_relevance"],
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

    logger.info(f"=== KrResearchCollector 시작: {target_date} ===")

    all_articles = []

    # RSS 병렬 수집
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {
            ex.submit(collect_rss, name, cfg): name
            for name, cfg in RESEARCH_RSS.items()
        }
        for fut in as_completed(futures):
            all_articles.extend(fut.result())

    # 스크래핑 순차 실행
    for name, cfg in RESEARCH_SCRAPE.items():
        all_articles.extend(scrape_target(name, cfg))

    # 기관 유형별 통계
    from collections import Counter
    org_counts = Counter(a["org_type"] for a in all_articles)
    logger.info(f"기관 유형별: {dict(org_counts)}")

    # 저장
    date_str = target_date.replace("-", "")
    out_path = RESEARCH_DIR / f"research_{date_str}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)

    logger.info(f"=== KrResearchCollector 완료: {len(all_articles)}건 → {out_path} ===")
    return out_path


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    d = sys.argv[1] if len(sys.argv) > 1 else None
    run(d)
