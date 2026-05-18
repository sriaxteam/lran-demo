"""
Manual Input Pipeline — V2
엑셀 기사 파일을 직접 제공하여 분석 파이프라인 실행
결과는 data_v2/ 에 저장되고 dashboard_v2.py 에서 확인

입력 엑셀 형식 (열 순서):
  언어 | 분류 | 미디어/언론사 | 발행일시(KST) | 제목 | 기사링크

사용법:
  python manual_input.py --file "경로/파일.xlsx"
  python manual_input.py --file "경로/파일.xlsx" --date 2026-05-04
  python manual_input.py --file "경로/파일.xlsx" --date 2026-05-04 --fetch-body
"""

# ── V2 데이터 루트 설정 (반드시 config import 전에 설정)
import os
os.environ["IRAN_DATA_DIR"] = "data_v2"

import argparse
import hashlib
import json
import logging
import sys
import time
from datetime import datetime, date
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    BASE_DIR, DATA_DIR, RAW_DIR, CLEAN_DIR, ANALYZED_DIR,
    COUNTRY_RESPONSE_DIR, POLICY_DIR, PARADIGM_DIR, DOMESTIC_DIR,
    USER_AGENT, REQUEST_DELAY,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False))],
)
logger = logging.getLogger("manual_input_v2")

HEADERS = {"User-Agent": USER_AGENT}

# ── 엑셀 컬럼 인덱스
COL_LANG, COL_CAT, COL_SOURCE, COL_DATE, COL_TITLE, COL_URL = 0, 1, 2, 3, 4, 5

CATEGORY_MAP = {
    "군사": "military",      "military": "military",
    "외교": "diplomacy",     "외교/정치": "diplomacy",  "정치": "diplomacy",
    "에너지": "energy",      "유가": "energy",
    "경제": "economy",       "경제/금융": "economy",    "금융": "economy",
    "인도주의": "humanitarian",
    "핵": "nuclear",         "핵무기": "nuclear",
    "한국": "korea",         "국내": "korea",
    "패러다임": "paradigm",
    "각국대응": "country_response",
}


def make_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def detect_lang(val: str) -> str:
    if "한국" in str(val).lower() or "ko" in str(val).lower():
        return "ko"
    return "en"


def map_category(val: str) -> str:
    for k, v in CATEGORY_MAP.items():
        if k in str(val):
            return v
    return "economy"


def fetch_body(url: str) -> str:
    try:
        time.sleep(REQUEST_DELAY)
        r = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        paragraphs = soup.select("article p, .article-body p, .content p, p")
        return " ".join(p.get_text(strip=True) for p in paragraphs[:10])[:500]
    except Exception:
        return ""


# ─────────────────────────────────────────────
# 엑셀 → raw JSON
# ─────────────────────────────────────────────

def excel_to_raw(file_path: str, target_date: str, fetch_body_flag: bool = False) -> Path:
    logger.info(f"[V2] 엑셀 로드: {file_path}")
    df = pd.read_excel(file_path, header=0)

    if len(df.columns) < 6:
        raise ValueError(f"컬럼 수 부족: {len(df.columns)}개 (최소 6개 필요)")

    articles, skipped = [], 0
    for idx, row in df.iterrows():
        try:
            title = str(row.iloc[COL_TITLE]).strip()
            url   = str(row.iloc[COL_URL]).strip()
            if not title or title == "nan" or not url.startswith("http"):
                skipped += 1
                continue

            pub_str = ""
            if not pd.isna(row.iloc[COL_DATE]):
                try:
                    pub_str = pd.to_datetime(row.iloc[COL_DATE]).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pub_str = str(row.iloc[COL_DATE])

            body = fetch_body(url) if fetch_body_flag else ""

            articles.append({
                "id":            make_id(url),
                "source":        str(row.iloc[COL_SOURCE]).strip() if not pd.isna(row.iloc[COL_SOURCE]) else "manual",
                "title":         title,
                "url":           url,
                "published":     pub_str,
                "summary":       body,
                "credibility":   8.0,
                "lang":          detect_lang(row.iloc[COL_LANG]),
                "category_hint": map_category(row.iloc[COL_CAT]),
                "collected_at":  datetime.utcnow().isoformat(),
                "input_mode":    "manual_v2",
            })
        except Exception as e:
            logger.warning(f"행 {idx} 처리 실패: {e}")
            skipped += 1

    logger.info(f"[V2] 변환 완료: {len(articles)}건 (건너뜀: {skipped}건)")

    date_str = target_date.replace("-", "")
    out_path = RAW_DIR / f"raw_{date_str}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    logger.info(f"[V2] raw 저장 → {out_path}")
    return out_path


# ─────────────────────────────────────────────
# Analyzer용 기사 선별 (Rate Limit 방지)
# ─────────────────────────────────────────────

_IRAN_KW = [
    "iran","hormuz","irgc","tehran","middle east","persian gulf",
    "이란","호르무즈","중동","유가","원유","에너지","봉쇄","전쟁","핵",
    "oil","crude","sanctions","nuclear","war","conflict","opec",
    "이스라엘","사우디","미국","houthi","후티","hezbollah","헤즈볼라",
]

def _trim_for_analyzer(clean_path: Path, max_items: int = 60) -> Path:
    """clean JSON에서 이란·중동 관련 상위 max_items건 선별 후 별도 파일로 저장"""
    with open(clean_path, encoding="utf-8") as f:
        articles = json.load(f)

    def _score(a):
        text = (a.get("title","") + " " + a.get("summary","")).lower()
        kw_hits = sum(1 for kw in _IRAN_KW if kw in text)
        cred    = a.get("credibility", 7.0)
        return kw_hits * 2 + cred

    scored = sorted(articles, key=_score, reverse=True)
    top    = scored[:max_items]

    out_path = clean_path.parent / clean_path.name.replace("clean_", "clean_top_")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(top, f, ensure_ascii=False, indent=2)

    logger.info(f"  선별: {len(articles)}건 → 상위 {len(top)}건 ({out_path.name})")
    return out_path


# ─────────────────────────────────────────────
# 파이프라인 실행
# ─────────────────────────────────────────────

def safe(name, fn, *args):
    try:
        result = fn(*args)
        logger.info(f"  ✓ {name}")
        return result
    except Exception as e:
        logger.error(f"  ✗ {name}: {e}", exc_info=True)
        return None


def run_pipeline(target_date: str, raw_path: Path):
    logger.info("=" * 55)
    logger.info(f"  [V2] 수동 입력 분석 파이프라인 - {target_date}")
    logger.info(f"  데이터 루트: {DATA_DIR}")
    logger.info("=" * 55)

    # Layer 2: 정제
    logger.info("[Layer 2] 중복 제거·정제...")
    import dedup
    clean_path = safe("dedup", dedup.run, raw_path)
    if not clean_path:
        logger.error("정제 실패. 중단.")
        return

    # Layer 3: Claude API 분석 (상위 60건만 — Rate Limit 방지)
    logger.info("[Layer 3] Claude API 분석 (상위 60건)...")
    trim_path = _trim_for_analyzer(clean_path, max_items=60)
    import analyzer
    analyzed_path = safe("analyzer", analyzer.run, trim_path)
    # 후속 모듈이 표준 파일명(analyzed_YYYYMMDD.json)을 기대하므로 복사
    if analyzed_path and analyzed_path.exists():
        import shutil
        date_str = target_date.replace("-", "")
        std_path = ANALYZED_DIR / f"analyzed_{date_str}.json"
        shutil.copy2(analyzed_path, std_path)
        logger.info(f"  표준 파일명으로 복사: {std_path.name}")
        analyzed_path = std_path

    import paradigm_detector
    safe("paradigm_detector", paradigm_detector.run, target_date)

    import country_response_tracker
    safe("country_response_tracker", country_response_tracker.run, target_date)

    import minseang_analyzer
    safe("minseang_analyzer", minseang_analyzer.run, target_date)

    # 국내 지표 (유가·환율은 자동수집과 공유)
    try:
        import domestic_tracker
        safe("domestic_tracker", domestic_tracker.run, target_date)
    except Exception:
        logger.info("  domestic_tracker 건너뜀")

    # Layer 4: 리포트
    logger.info("[Layer 4] 리포트 생성...")
    import reporter
    safe("reporter", reporter.run, analyzed_path or clean_path)

    logger.info("=" * 55)
    logger.info(f"  [V2] 완료! dashboard_v2.py 에서 {target_date} 탭을 확인하세요.")
    logger.info("=" * 55)


def infer_date(file_path: str) -> str:
    try:
        df = pd.read_excel(file_path, header=0, usecols=[COL_DATE])
        dates = pd.to_datetime(df.iloc[:, 0], errors="coerce").dropna()
        if len(dates):
            latest = dates.max().strftime("%Y-%m-%d")
            logger.info(f"[V2] 날짜 자동 감지: {latest}")
            return latest
    except Exception:
        pass
    return date.today().strftime("%Y-%m-%d")


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="[V2] 엑셀 기사 파일 → 분석 파이프라인 (data_v2/ 저장)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python manual_input.py --file "C:/path/to/뉴스크롤링.xlsx"
  python manual_input.py --file "C:/path/to/뉴스크롤링.xlsx" --date 2026-05-04
  python manual_input.py --file "C:/path/to/뉴스크롤링.xlsx" --fetch-body
        """,
    )
    parser.add_argument("--file",         required=True, help="엑셀 파일 경로 (.xlsx)")
    parser.add_argument("--date",         default=None,  help="분석 날짜 YYYY-MM-DD")
    parser.add_argument("--fetch-body",   action="store_true", help="URL에서 기사 본문 수집")
    parser.add_argument("--convert-only", action="store_true", help="변환만, 파이프라인 실행 안 함")
    args = parser.parse_args()

    target_date = args.date or infer_date(args.file)
    raw_path    = excel_to_raw(args.file, target_date, fetch_body_flag=args.fetch_body)

    if not args.convert_only:
        run_pipeline(target_date, raw_path)
