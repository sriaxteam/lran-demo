"""
Paradigm Detector
패러다임 변화 신호 감지 에이전트

입력:
  - data/intl/intl_YYYYMMDD.json     (국제기구 발표)
  - data/research/research_YYYYMMDD.json  (한국연구 + 싱크탱크)
  - data/analyzed/analyzed_YYYYMMDD.json  (일반 뉴스 분석 결과)

처리:
  1. 3개 JSON에서 패러다임 변화 신호 후보 기사 필터링
  2. Claude API로 신호 분류 및 중요도 평가
  3. 주간 누적 DB에서 반복 패턴 감지 → 구조적 변화 판단

출력:
  - data/paradigm/paradigm_YYYYMMDD.json
    {
      "date": "2026-04-16",
      "signals": [            ← 오늘 감지된 패러다임 변화 신호
        {
          "signal_id": "...",
          "category": "에너지안보재편|무역질서변화|정책패러다임|지역질서재편",
          "title_ko": "신호 제목 (한국어)",
          "description": "신호 설명 (3줄)",
          "evidence": ["근거 기사 제목 1", "근거 기사 제목 2"],
          "strength": 1~5,     ← 신호 강도 (5=구조적 변화 확정)
          "trend": "신규|강화|약화|반전",
          "suwon_implication": "수원시 민생·정책에 주는 함의",
          "sources": ["IEA", "IMF", "OECD"],
          "first_detected": "YYYY-MM-DD",
        }
      ],
      "summary_ko": "오늘 전체 패러다임 변화 요약 (5줄 이내)",
      "weekly_trend": {...}    ← 주간 누적 트렌드
    }
"""

import json
import logging
import sqlite3
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import anthropic

from config import (
    ANTHROPIC_API_KEY, DATA_DIR, DB_PATH, CLAUDE_MODEL,
)

logger = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

PARADIGM_DIR = DATA_DIR / "paradigm"
PARADIGM_DIR.mkdir(parents=True, exist_ok=True)

INTL_DIR    = DATA_DIR / "intl"
RESEARCH_DIR = DATA_DIR / "research"
ANALYZED_DIR = DATA_DIR / "analyzed"

# ─────────────────────────────────────────────
# 패러다임 카테고리 정의
# ─────────────────────────────────────────────

PARADIGM_CATEGORIES = {
    "에너지안보재편": {
        "desc": "글로벌 에너지 공급·안보 구조가 근본적으로 변화하는 신호",
        "keywords": ["energy security", "energy transition", "supply diversification",
                     "strategic reserve", "energy partnership", "reliability",
                     "에너지안보", "에너지전환", "에너지다변화"],
        "suwon_link": "수원시 에너지 비용 구조, 난방비·전기료 장기 전망에 직결",
    },
    "무역공급망재편": {
        "desc": "국제 무역·공급망·해운 질서가 구조적으로 변화하는 신호",
        "keywords": ["supply chain", "trade disruption", "shipping route",
                     "hormuz alternative", "trade fragmentation", "decoupling",
                     "공급망", "무역질서", "해운항로"],
        "suwon_link": "수원시 제조기업 납품 비용, 수출기업 공급망 불안에 영향",
    },
    "정책패러다임전환": {
        "desc": "주요국·국제기구의 경제·에너지 정책 방향 자체가 바뀌는 신호",
        "keywords": ["price cap", "export controls", "hoarding", "emergency measures",
                     "paradigm shift", "policy reversal", "government intervention",
                     "가격상한", "수출통제", "정책전환", "직접지원"],
        "suwon_link": "수원시 민생안정 정책 설계의 국제 벤치마킹 기준 변화",
    },
    "지역질서재편": {
        "desc": "중동 및 글로벌 지정학적 질서가 구조적으로 변화하는 신호",
        "keywords": ["regional order", "geopolitical", "fragmentation", "alliance",
                     "middle east order", "normalization", "isolation",
                     "지역질서", "지정학", "동맹재편"],
        "suwon_link": "장기 에너지 수입 안정성, 수원시 외국인 근로자 동향에 간접 영향",
    },
    "민생충격패턴": {
        "desc": "전쟁이 각국 일반 시민 생활에 구조적 충격을 주는 패턴",
        "keywords": ["inflation", "cost of living", "food security", "poverty",
                     "vulnerable", "household", "recession risk",
                     "물가상승", "생활비", "식량안보", "취약계층", "경기침체"],
        "suwon_link": "수원시 취약계층 지원, 민생안정 긴급 대책 수립의 직접 근거",
    },
}

SYSTEM_PROMPT = """당신은 수원시정연구원의 정책 분석 전문가입니다.
이란-미국 전쟁(2026)과 관련된 기사·보고서를 분석해서 단순 사건 보도가 아닌
'구조적 변화·패러다임 전환 신호'를 감지하는 역할을 합니다.

반드시 JSON 형식으로만 응답하세요. 다른 텍스트나 마크다운 없이 순수 JSON만 출력하세요."""

DETECTION_PROMPT = """다음 기사·보고서 목록에서 단순 사건 보도가 아닌
'패러다임 변화 신호'를 감지해서 JSON으로 반환하세요.

패러다임 변화 신호란: 일회성 사건이 아니라 구조적·중장기적 변화를 예고하는 신호입니다.
예: "IEA 사무총장이 에너지 파트너십이 가격→신뢰 기준으로 전환될 것이라고 선언"

입력 기사 목록:
{articles_json}

패러다임 카테고리:
{categories_json}

반환 형식 (JSON 배열):
[
  {{
    "signal_id": "sig_001",
    "category": "에너지안보재편",
    "title_ko": "신호 제목 (한국어, 20자 이내)",
    "description": "신호 설명 3줄 (각 줄 • 시작, \\n 구분)",
    "evidence_titles": ["근거 기사 제목 1", "근거 기사 제목 2"],
    "evidence_sources": ["IEA", "IMF"],
    "strength": 4,
    "trend": "신규",
    "suwon_implication": "수원시 민생·정책에 주는 함의 (2줄 이내)",
    "is_structural": true
  }}
]

신호가 없으면 빈 배열 [] 반환.
strength 기준: 1=미약한 징후, 2=주목할 변화, 3=중요한 전환, 4=구조적 변화 시작, 5=패러다임 전환 확정
trend: 신규(처음 감지) / 강화(기존 신호 심화) / 약화(기존 신호 감소) / 반전(기존 흐름 역전)"""

SUMMARY_PROMPT = """다음 오늘의 패러다임 변화 신호 목록을 바탕으로
수원시정연구원 원장님께 보고할 요약문을 작성해주세요.

신호 목록:
{signals_json}

반환 형식 (JSON):
{{
  "summary_ko": "오늘의 패러다임 변화 전체 요약 (5줄 이내, 각 줄 • 시작, \\n 구분)",
  "top_signal": "가장 중요한 신호 제목",
  "suwon_action": "수원시가 오늘 당장 주목해야 할 것 (2줄 이내)"
}}"""


# ─────────────────────────────────────────────
# 1. 후보 기사 필터링
# ─────────────────────────────────────────────

def load_candidates(date_str: str) -> list:
    """3개 소스에서 패러다임 변화 후보 기사 로드"""
    candidates = []

    # 국제기구 발표 (paradigm_weight 3 이상)
    intl_path = INTL_DIR / f"intl_{date_str}.json"
    if intl_path.exists():
        with open(intl_path, encoding="utf-8") as f:
            intl = json.load(f)
        candidates += [a for a in intl if a.get("paradigm_weight", 0) >= 3]
        logger.info(f"국제기구 후보: {len([a for a in intl if a.get('paradigm_weight',0)>=3])}건")

    # 연구기관·싱크탱크 (전체 포함)
    research_path = RESEARCH_DIR / f"research_{date_str}.json"
    if research_path.exists():
        with open(research_path, encoding="utf-8") as f:
            research = json.load(f)
        candidates += research
        logger.info(f"연구기관 후보: {len(research)}건")

    # 일반 뉴스 중 중요도 4~5 + 패러다임 키워드 포함
    analyzed_path = ANALYZED_DIR / f"analyzed_{date_str}.json"
    if analyzed_path.exists():
        with open(analyzed_path, encoding="utf-8") as f:
            analyzed = json.load(f)
        high_importance = [
            a for a in analyzed
            if a.get("importance", 0) >= 4
            and a.get("credibility", 0) >= 8.5
        ]
        candidates += high_importance
        logger.info(f"주요 뉴스 후보: {len(high_importance)}건")

    logger.info(f"전체 패러다임 감지 후보: {len(candidates)}건")
    return candidates


# ─────────────────────────────────────────────
# 2. 주간 누적 트렌드 (SQLite)
# ─────────────────────────────────────────────

def init_paradigm_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS paradigm_signals (
            signal_id      TEXT,
            detected_date  TEXT,
            category       TEXT,
            title_ko       TEXT,
            strength       INTEGER,
            trend          TEXT,
            is_structural  INTEGER,
            suwon_implication TEXT,
            sources        TEXT,
            PRIMARY KEY (signal_id, detected_date)
        )
    """)
    conn.commit()
    conn.close()


def save_signals_to_db(signals: list, detected_date: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for s in signals:
        try:
            cur.execute("""
                INSERT OR REPLACE INTO paradigm_signals
                (signal_id, detected_date, category, title_ko, strength,
                 trend, is_structural, suwon_implication, sources)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                s.get("signal_id", ""),
                detected_date,
                s.get("category", ""),
                s.get("title_ko", ""),
                s.get("strength", 1),
                s.get("trend", "신규"),
                int(s.get("is_structural", False)),
                s.get("suwon_implication", ""),
                json.dumps(s.get("evidence_sources", []), ensure_ascii=False),
            ))
        except Exception as e:
            logger.warning(f"DB 저장 실패: {e}")
    conn.commit()
    conn.close()


def get_weekly_trend() -> dict:
    """최근 7일 패러다임 신호 누적 집계"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cutoff = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        cur.execute("""
            SELECT category, COUNT(*) as cnt, MAX(strength) as max_str
            FROM paradigm_signals
            WHERE detected_date >= ?
            GROUP BY category
            ORDER BY cnt DESC
        """, (cutoff,))
        rows = cur.fetchall()
        conn.close()
        return {
            row[0]: {"count": row[1], "max_strength": row[2]}
            for row in rows
        }
    except Exception:
        return {}


# ─────────────────────────────────────────────
# 3. Claude API 분석
# ─────────────────────────────────────────────

def detect_signals_with_claude(candidates: list) -> list:
    """Claude API로 패러다임 변화 신호 감지"""
    if not candidates:
        return []

    # 분석용 요약 (토큰 절약)
    articles_for_prompt = [
        {
            "source":    a.get("source", ""),
            "org_type":  a.get("org_type", ""),
            "title":     a.get("title", ""),
            "summary":   a.get("summary", "")[:200],
            "credibility": a.get("credibility", 0),
        }
        for a in candidates[:40]  # 최대 40건
    ]

    categories_summary = {
        cat: {"설명": v["desc"], "수원시연결": v["suwon_link"]}
        for cat, v in PARADIGM_CATEGORIES.items()
    }

    prompt = DETECTION_PROMPT.format(
        articles_json=json.dumps(articles_for_prompt, ensure_ascii=False, indent=2),
        categories_json=json.dumps(categories_summary, ensure_ascii=False, indent=2),
    )

    try:
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=8096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip().replace("```json", "").replace("```", "").strip()
        signals = json.loads(raw)
        return signals if isinstance(signals, list) else []
    except json.JSONDecodeError as e:
        logger.warning(f"[ParadigmDetector] JSON 파싱 실패: {e}")
        return []
    except Exception as e:
        logger.warning(f"[ParadigmDetector] Claude API 실패: {e}")
        return []


def generate_summary(signals: list) -> dict:
    """오늘의 패러다임 변화 요약 생성"""
    if not signals:
        return {
            "summary_ko": "• 오늘은 특별한 패러다임 변화 신호가 감지되지 않았습니다.",
            "top_signal": "없음",
            "suwon_action": "• 기존 모니터링 유지",
        }

    prompt = SUMMARY_PROMPT.format(
        signals_json=json.dumps(signals, ensure_ascii=False, indent=2)
    )

    try:
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=800,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"[ParadigmDetector] 요약 생성 실패: {e}")
        return {
            "summary_ko": f"• 오늘 {len(signals)}개 패러다임 변화 신호 감지됨.",
            "top_signal": signals[0].get("title_ko", "") if signals else "없음",
            "suwon_action": "• 상세 신호 목록 확인 필요",
        }


# ─────────────────────────────────────────────
# 4. 메인
# ─────────────────────────────────────────────

def run(target_date: str = None) -> Path:
    if target_date is None:
        target_date = date.today().strftime("%Y-%m-%d")

    date_str = target_date.replace("-", "")
    logger.info(f"=== ParadigmDetector 시작: {target_date} ===")

    # DB 초기화
    init_paradigm_db()

    # 후보 기사 로드
    candidates = load_candidates(date_str)

    if not candidates:
        logger.warning("패러다임 감지 후보 없음. 국제기구·연구기관 수집 결과 확인 필요.")

    # Claude API로 신호 감지
    logger.info(f"Claude API 패러다임 신호 감지 중 ({len(candidates)}건 분석)...")
    signals = detect_signals_with_claude(candidates)

    # 날짜·first_detected 추가
    for sig in signals:
        sig["detected_date"] = target_date
        if sig.get("trend") == "신규":
            sig["first_detected"] = target_date

    # DB 저장
    save_signals_to_db(signals, target_date)

    # 주간 트렌드
    weekly_trend = get_weekly_trend()

    # 요약 생성
    summary_data = generate_summary(signals)

    # 카테고리별 집계
    by_category = defaultdict(list)
    for s in signals:
        by_category[s.get("category", "기타")].append(s)

    # 최종 출력 구성
    output = {
        "date":          target_date,
        "total_signals": len(signals),
        "structural_signals": len([s for s in signals if s.get("is_structural")]),
        "signals":       sorted(signals, key=lambda x: x.get("strength", 0), reverse=True),
        "by_category":   {k: len(v) for k, v in by_category.items()},
        "summary_ko":    summary_data.get("summary_ko", ""),
        "top_signal":    summary_data.get("top_signal", ""),
        "suwon_action":  summary_data.get("suwon_action", ""),
        "weekly_trend":  weekly_trend,
        "generated_at":  datetime.utcnow().isoformat(),
    }

    # 저장
    out_path = PARADIGM_DIR / f"paradigm_{date_str}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 로그 요약
    logger.info(f"감지된 신호: {len(signals)}개 | 구조적 변화: {output['structural_signals']}개")
    logger.info(f"카테고리별: {output['by_category']}")
    logger.info(f"=== ParadigmDetector 완료 → {out_path} ===")
    return out_path


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    d = sys.argv[1] if len(sys.argv) > 1 else None
    run(d)
