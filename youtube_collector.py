"""
YouTube Collector v2 — 검색 기반 수집
특정 채널 고정이 아닌 YouTube 전체에서 중동-미국 전쟁 관련
최신 뉴스·전문가 분석·브리핑을 검색해서 수집

YouTube Data API search → 자막 추출 → Claude 한국어 요약
출력: data/youtube/yt_summary_YYYYMMDD.json
"""

import json
import logging
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

from config import (
    YT_DIR, YT_API_KEY,
    YOUTUBE_SCHEDULE_DAYS,
    ANTHROPIC_API_KEY, CLAUDE_MODEL,
)

logger = logging.getLogger(__name__)

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    _yt_api = YouTubeTranscriptApi()
    YT_AVAILABLE = True
except ImportError:
    _yt_api = None
    YT_AVAILABLE = False
    logger.warning("youtube-transcript-api 미설치")

import anthropic
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# ─────────────────────────────────────────────
# 검색 쿼리 목록 — 영어·한국어 번갈아 검색
# ─────────────────────────────────────────────
SEARCH_QUERIES = [
    # 영어 — 전문가 분석 / 최신 뉴스
    {"q": "Iran US war 2026 expert analysis",           "hl": "en", "order": "relevance"},
    {"q": "Iran war Middle East latest news",           "hl": "en", "order": "date"},
    {"q": "Hormuz strait Iran blockade oil",            "hl": "en", "order": "relevance"},
    {"q": "Iran nuclear deal war ceasefire",            "hl": "en", "order": "date"},
    {"q": "Middle East war expert opinion 2026",        "hl": "en", "order": "relevance"},
    # 한국어 — 전문가·뉴스 채널
    {"q": "이란 전쟁 전문가 분석",                      "hl": "ko", "order": "relevance"},
    {"q": "중동전쟁 최신 뉴스 2026",                    "hl": "ko", "order": "date"},
    {"q": "이란 미국 전쟁 유가 영향",                   "hl": "ko", "order": "relevance"},
    {"q": "호르무즈 봉쇄 에너지 위기",                  "hl": "ko", "order": "date"},
]

# 검색 결과 최대 건수 (쿼리당) — API 쿼터 절약
MAX_PER_QUERY = 5
# 최종 처리할 고유 영상 최대 수
MAX_VIDEOS_TO_PROCESS = 10
# 수집 기준: 최근 N일 이내 영상만
PUBLISHED_WITHIN_DAYS = 7


def should_run_today() -> bool:
    return datetime.today().weekday() in YOUTUBE_SCHEDULE_DAYS


def search_youtube(query: str, hl: str, order: str,
                   max_results: int = MAX_PER_QUERY,
                   published_after_days: int = PUBLISHED_WITHIN_DAYS) -> list:
    """YouTube Data API로 검색 — 영상 목록 반환"""
    if not YT_API_KEY:
        return []
    try:
        after = (datetime.utcnow() - timedelta(days=published_after_days)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        params = {
            "key":              YT_API_KEY,
            "q":                query,
            "part":             "snippet",
            "type":             "video",
            "order":            order,
            "maxResults":       max_results,
            "publishedAfter":   after,
            "relevanceLanguage": hl,
            "videoDuration":    "medium",   # 4~20분 — 쇼츠 제외
        }
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params=params, timeout=10,
        )
        if r.status_code != 200:
            logger.warning(f"[YT Search] '{query}' HTTP {r.status_code}")
            return []
        results = []
        for item in r.json().get("items", []):
            vid  = item.get("id", {}).get("videoId", "")
            snip = item.get("snippet", {})
            if not vid:
                continue
            results.append({
                "video_id":    vid,
                "title":       snip.get("title", ""),
                "channel":     snip.get("channelTitle", ""),
                "published":   snip.get("publishedAt", ""),
                "url":         f"https://www.youtube.com/watch?v={vid}",
                "query":       query,
                "lang":        hl,
            })
        logger.info(f"  [검색] '{query[:30]}' → {len(results)}건")
        return results
    except Exception as e:
        logger.warning(f"[YT Search] 실패: {e}")
        return []


def extract_transcript(video_id: str, lang: str = "en") -> str:
    """자막 추출 — 영어·한국어 순으로 시도"""
    if not YT_AVAILABLE or _yt_api is None:
        return ""
    try:
        lang_codes = ["ko", "en"] if lang == "ko" else ["en", "ko"]
        transcript = None
        for lc in lang_codes:
            try:
                transcript = _yt_api.fetch(video_id, languages=[lc])
                break
            except Exception:
                continue
        if transcript is None:
            transcript = _yt_api.fetch(video_id)
        return " ".join(s.text for s in transcript)[:6000]
    except Exception as e:
        logger.warning(f"[자막] {video_id} 실패: {str(e)[:80]}")
        return ""


def summarize_with_claude(title: str, transcript: str,
                          channel: str, lang: str) -> dict:
    """자막(없으면 제목)을 Claude로 분석"""
    if not transcript:
        transcript = f"[자막 없음 — 제목 기반 분석] {title}"

    safe_t  = transcript.replace("\\", " ").replace('"', "'")[:4000]
    safe_ti = title.replace("\\", " ").replace('"', "'")

    prompt = f"""아래 YouTube 영상을 분석해 JSON을 반환하세요.
채널: {channel}
제목: {safe_ti}
자막: {safe_t}

반환 형식(JSON만, 코드블록 없이):
{{"summary_ko":"• 핵심1\\n• 핵심2\\n• 핵심3","key_points":["포인트1","포인트2","포인트3"],"iran_relevance":"높음","content_type":"뉴스|전문가분석|브리핑|기타","suwon_connection":"수원시 민생 연결점"}}

iran_relevance: 높음/중간/낮음
content_type: 뉴스, 전문가분석, 브리핑, 기타 중 하나"""

    try:
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=800,
            system="이란-중동 전쟁 전문 분석가. 반드시 유효한 JSON 한 줄만 반환.",
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        raw = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                return json.loads(m.group())
            raise
    except Exception as e:
        logger.warning(f"[Claude] 요약 실패: {e}")
        return {"summary_ko": f"요약 실패: {title}",
                "key_points": [], "iran_relevance": "중간", "content_type": "기타"}


def load_existing(out_path: Path) -> list:
    if out_path.exists():
        try:
            return json.load(open(out_path, encoding="utf-8")).get("summaries", [])
        except Exception:
            pass
    return []


# ─────────────────────────────────────────────
# 메인 실행
# ─────────────────────────────────────────────
def run(target_date: str = None) -> Path:
    if target_date is None:
        target_date = date.today().strftime("%Y-%m-%d")

    date_str = target_date.replace("-", "")
    out_path = YT_DIR / f"yt_summary_{date_str}.json"

    logger.info(f"=== YouTubeCollector v2 시작: {target_date} ===")

    # 비수집일: 기존 파일 유지
    if not should_run_today():
        logger.info("비수집일 — 기존 파일 유지")
        if not out_path.exists():
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump({"date": target_date, "summaries": [], "note": "비수집일"},
                          f, ensure_ascii=False)
        return out_path

    if not YT_API_KEY:
        logger.error("YT_API_KEY 없음 — 수집 불가")
        return out_path

    # ── 1단계: 검색 ──
    all_candidates = []
    seen_ids = set()
    for query_cfg in SEARCH_QUERIES:
        results = search_youtube(
            query=query_cfg["q"],
            hl=query_cfg["hl"],
            order=query_cfg["order"],
        )
        for v in results:
            if v["video_id"] not in seen_ids:
                seen_ids.add(v["video_id"])
                all_candidates.append(v)
        time.sleep(0.5)   # API 레이트 리밋 방지

    logger.info(f"검색 완료: 고유 영상 {len(all_candidates)}건")

    if not all_candidates:
        existing = load_existing(out_path)
        if existing:
            logger.warning("검색 결과 0건 — 기존 데이터 유지")
            return out_path
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"date": target_date, "total": 0, "summaries": [],
                       "note": "검색 실패"}, f, ensure_ascii=False)
        return out_path

    # ── 2단계: 자막 추출 + Claude 요약 ──
    all_summaries = []
    processed = 0

    for video in all_candidates:
        if processed >= MAX_VIDEOS_TO_PROCESS:
            break

        vid   = video["video_id"]
        title = video["title"]
        lang  = video["lang"]

        logger.info(f"  → [{lang.upper()}] {title[:55]}")
        transcript = extract_transcript(vid, lang)
        time.sleep(1)

        analysis = summarize_with_claude(title, transcript, video["channel"], lang)

        if analysis.get("iran_relevance") == "낮음":
            logger.info(f"     관련성 낮음 — 스킵")
            continue

        all_summaries.append({
            "channel":          video["channel"],
            "video_id":         vid,
            "title":            title,
            "url":              video["url"],
            "published":        video["published"],
            "lang":             lang,
            "search_query":     video["query"],
            "summary_ko":       analysis.get("summary_ko", ""),
            "key_points":       analysis.get("key_points", []),
            "iran_relevance":   analysis.get("iran_relevance", "중간"),
            "content_type":     analysis.get("content_type", "기타"),
            "suwon_connection": analysis.get("suwon_connection", ""),
            "collected_at":     datetime.utcnow().isoformat(),
            "data_type":        "youtube",
        })
        processed += 1
        time.sleep(2)

    # ── 0건이면 기존 유지 ──
    if not all_summaries:
        existing = load_existing(out_path)
        if existing:
            logger.warning(f"분석 결과 0건 — 기존 {len(existing)}건 유지")
            return out_path

    # ── 관련성 높은 순 정렬 ──
    _rel = {"높음": 0, "중간": 1, "낮음": 2}
    _type_priority = {"전문가분석": 0, "브리핑": 1, "뉴스": 2, "기타": 3}
    all_summaries.sort(key=lambda x: (
        _rel.get(x.get("iran_relevance", "중간"), 1),
        _type_priority.get(x.get("content_type", "기타"), 3),
    ))

    output = {
        "date":      target_date,
        "total":     len(all_summaries),
        "summaries": all_summaries,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"=== YouTubeCollector 완료: {len(all_summaries)}건 → {out_path} ===")
    return out_path


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    run(sys.argv[1] if len(sys.argv) > 1 else None)
