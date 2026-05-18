"""
Deduplicator Agent
raw_YYYYMMDD.json + intl_YYYYMMDD.json + research_YYYYMMDD.json 를 합산한 후
  - URL 기준 중복 제거
  - 제목 유사도 기반 중복 제거
  - 오늘 날짜 기사만 필터 (옵션)
→ data/clean/clean_YYYYMMDD.json 저장
"""

import json
import logging
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from config import RAW_DIR, CLEAN_DIR, DATA_DIR

INTL_DIR     = DATA_DIR / "intl"
RESEARCH_DIR = DATA_DIR / "research"

logger = logging.getLogger(__name__)


def normalize_title(title: str) -> str:
    """비교용 제목 정규화: 소문자, 특수문자 제거, 공백 통일"""
    t = title.lower()
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def titles_similar(t1: str, t2: str, threshold: float = 0.75) -> bool:
    """단어 자카드 유사도"""
    s1 = set(normalize_title(t1).split())
    s2 = set(normalize_title(t2).split())
    if not s1 or not s2:
        return False
    intersection = s1 & s2
    union = s1 | s2
    return len(intersection) / len(union) >= threshold


def is_recent(published: str, days: int = 2) -> bool:
    """발행일이 최근 N일 이내인지 확인. 날짜 파싱 실패 시 True(포함) 처리"""
    if not published:
        return True
    cutoff = datetime.utcnow() - timedelta(days=days)
    for fmt in [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
        "%Y-%m-%d",
    ]:
        try:
            dt = datetime.strptime(published[:25], fmt)
            dt = dt.replace(tzinfo=None)
            return dt >= cutoff
        except ValueError:
            continue
    return True  # 파싱 실패 시 포함


def run(raw_path: Path) -> Path:
    logger.info(f"=== Deduplicator 시작: {raw_path.name} ===")

    # 날짜 코드 추출 (raw_20260420.json → 20260420)
    date_str = raw_path.stem.replace("raw_", "")

    # ── 1. 수집 소스 통합 로드 ──────────────────────────────
    articles = []

    # (A) 일반 뉴스 (collector.py)
    with open(raw_path, encoding="utf-8") as f:
        raw_articles = json.load(f)
    for a in raw_articles:
        a.setdefault("data_type", "news")
    articles.extend(raw_articles)
    logger.info(f"  뉴스(raw):     {len(raw_articles)}건")

    # (B) 국제기구 보고서 (intl_org_collector.py)
    intl_path = INTL_DIR / f"intl_{date_str}.json"
    if intl_path.exists():
        with open(intl_path, encoding="utf-8") as f:
            intl_articles = json.load(f)
        for a in intl_articles:
            a.setdefault("data_type", "intl_org")
        articles.extend(intl_articles)
        logger.info(f"  국제기구(intl): {len(intl_articles)}건")
    else:
        logger.info(f"  국제기구 파일 없음 ({intl_path.name})")

    # (C) 국내외 연구기관 (kr_research_collector.py)
    research_path = RESEARCH_DIR / f"research_{date_str}.json"
    if research_path.exists():
        with open(research_path, encoding="utf-8") as f:
            research_articles = json.load(f)
        for a in research_articles:
            a.setdefault("data_type", "research")
        articles.extend(research_articles)
        logger.info(f"  연구기관(research): {len(research_articles)}건")
    else:
        logger.info(f"  연구기관 파일 없음 ({research_path.name})")

    logger.info(f"통합 원본: {len(articles)}건")

    # ── 2. 중복 제거 ────────────────────────────────────────
    # 1단계: URL 기준 중복 제거
    seen_urls = set()
    url_deduped = []
    for a in articles:
        url = a.get("url", "").split("?")[0].rstrip("/")  # 쿼리스트링 제거
        if url and url not in seen_urls:
            seen_urls.add(url)
            url_deduped.append(a)

    logger.info(f"URL 중복 제거 후: {len(url_deduped)}건")

    # 2단계: 날짜 필터 (최근 2일 이내)
    date_filtered = [a for a in url_deduped if is_recent(a.get("published", ""), days=2)]
    logger.info(f"날짜 필터 후: {len(date_filtered)}건")

    # 3단계: 제목 유사도 기반 중복 제거 (공신력 높은 것 우선 유지)
    # 공신력 내림차순 정렬 후 비교
    date_filtered.sort(key=lambda x: x.get("credibility", 0), reverse=True)

    final = []
    for candidate in date_filtered:
        title_c = candidate.get("title", "")
        duplicate = False
        for kept in final:
            if titles_similar(title_c, kept.get("title", "")):
                duplicate = True
                break
        if not duplicate:
            final.append(candidate)

    logger.info(f"제목 유사도 중복 제거 후: {len(final)}건")

    # 저장
    date_str = raw_path.stem.replace("raw_", "")
    out_path = CLEAN_DIR / f"clean_{date_str}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    logger.info(f"=== Deduplicator 완료: {len(final)}건 → {out_path} ===")
    return out_path


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else sorted(RAW_DIR.glob("raw_*.json"))[-1]
    run(path)
