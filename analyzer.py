"""
Analyzer Agent
clean_YYYYMMDD.json 기사를 Claude API로 분석:
  - 이슈 카테고리 분류 (military/diplomacy/energy/economy/humanitarian/nuclear/korea)
  - 한국어 3줄 요약
  - 핵심 키워드 추출 (인물, 지명, 사건)
  - 중요도 점수 (1~5)
→ data/analyzed/analyzed_YYYYMMDD.json 저장
"""

import json
import logging
import time
from pathlib import Path

import anthropic

from config import (
    ANTHROPIC_API_KEY, CLEAN_DIR, ANALYZED_DIR,
    CLAUDE_MODEL, ANALYZER_MODEL, ANALYZER_BATCH_SIZE, ISSUE_CATEGORIES,
)

logger = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """당신은 이란-미국 전쟁(2026) 전문 뉴스 분석가입니다.
주어진 기사 목록을 분석해서 반드시 JSON 형식으로만 응답하세요.
다른 텍스트, 설명, 마크다운 코드블록 없이 순수 JSON 배열만 출력하세요."""

USER_PROMPT_TEMPLATE = """다음 기사 목록을 분석해서 JSON 배열로 반환하세요.

기사 목록:
{articles_json}

각 기사에 대해 다음 필드를 포함한 JSON 객체를 반환하세요:
- id: 원본 id 그대로
- category: 다음 중 하나 → military / diplomacy / energy / economy / humanitarian / nuclear / korea / paradigm / country_response
- summary_ko: 한국어 3줄 요약 (각 줄은 "• "로 시작, \\n으로 구분)
- keywords: 핵심 키워드 배열 (인물명, 지명, 사건명 최대 5개)
- importance: 중요도 1~5 (5=최고, 오늘 전황에 미치는 영향 기준)
- reason: 분류 이유 한 문장 (한국어)
- related_country: 이 기사와 관련된 국가·세력 배열 (예: ["중국","러시아"]) — 해당 없으면 빈 배열

카테고리 선택 기준:
- country_response: 특정 국가·세력이 이란전쟁에 대해 취하는 행동·성명·정책 변화
- paradigm: 기존 지정학·에너지·군사·경제 질서가 변화하는 신호나 분석

반환 예시:
[
  {{
    "id": "abc123",
    "category": "country_response",
    "summary_ko": "• 중국이 이란-미국 전쟁 중재 의사를 공식 표명했다.\\n• 왕이 외교부장이 테헤란·워싱턴 모두와 접촉 중이다.\\n• 호르무즈 봉쇄 해제를 최우선 요구로 제시했다.",
    "keywords": ["왕이", "중국", "중재", "호르무즈", "외교"],
    "importance": 5,
    "reason": "중국의 공식 중재 개입은 전쟁 출구전략의 핵심 분기점",
    "related_country": ["중국", "이란", "미국"]
  }}
]"""


def analyze_batch(batch: list[dict]) -> list[dict]:
    """기사 배치를 Claude API로 분석"""
    articles_for_prompt = [
        {
            "id":      a["id"],
            "title":   a["title"],
            "summary": a.get("summary", ""),
            "source":  a["source"],
        }
        for a in batch
    ]

    prompt = USER_PROMPT_TEMPLATE.format(
        articles_json=json.dumps(articles_for_prompt, ensure_ascii=False, indent=2)
    )

    try:
        resp = client.messages.create(
            model=ANALYZER_MODEL,
            max_tokens=8000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()

        # JSON 파싱 (코드블록 제거 후)
        raw = raw.replace("```json", "").replace("```", "").strip()
        results = json.loads(raw)
        return results if isinstance(results, list) else []

    except json.JSONDecodeError as e:
        logger.warning(f"[Analyzer] JSON 파싱 실패: {e}")
        return []
    except Exception as e:
        logger.warning(f"[Analyzer] API 호출 실패: {e}")
        return []


FILTER_KEYWORDS = [
    "iran","hormuz","irgc","tehran","sanction","missile","nuclear",
    "houthi","hezbollah","israel","persian gulf","oil price","crude",
    "energy crisis","lng","middle east","war","blockade","strait",
    "이란","호르무즈","중동","유가","에너지","봉쇄","핵","미사일",
    "후티","헤즈볼라","이스라엘","전쟁","원유","도시가스","물가",
]

def is_relevant(article: dict) -> bool:
    """이란·중동 관련 기사 여부 키워드 기반 필터링"""
    text = (article.get("title", "") + " " + article.get("summary", "")).lower()
    return any(kw in text for kw in FILTER_KEYWORDS)


def run(clean_path: Path) -> Path:
    logger.info(f"=== Analyzer 시작: {clean_path.name} ===")

    with open(clean_path, encoding="utf-8") as f:
        articles = json.load(f)

    logger.info(f"전체 기사: {len(articles)}건")

    # ── 사전 필터링: 이란·중동 관련 기사만 분석
    relevant   = [a for a in articles if is_relevant(a)]
    irrelevant = [a for a in articles if not is_relevant(a)]
    logger.info(f"키워드 필터 후 분석 대상: {len(relevant)}건 (제외: {len(irrelevant)}건)")

    # 분석 결과 매핑 (id → 분석 결과)
    analysis_map: dict[str, dict] = {}

    # 배치 처리 (관련 기사만)
    batches = [relevant[i:i+ANALYZER_BATCH_SIZE] for i in range(0, len(relevant), ANALYZER_BATCH_SIZE)]
    for idx, batch in enumerate(batches):
        logger.info(f"배치 {idx+1}/{len(batches)} 분석 중 ({len(batch)}건)...")
        results = analyze_batch(batch)
        for r in results:
            if "id" in r:
                analysis_map[r["id"]] = r
        time.sleep(1)  # API 레이트 리밋 방지

    # 원본 기사에 분석 결과 병합 (필터 제외 기사는 category=filtered, importance=0)
    analyzed = []
    for article in articles:
        analysis = analysis_map.get(article["id"], {})
        is_filtered = not is_relevant(article)
        merged = {
            **article,
            "category":        "filtered" if is_filtered else analysis.get("category", "unknown"),
            "summary_ko":      analysis.get("summary_ko", ""),
            "keywords":        analysis.get("keywords", []),
            "importance":      0 if is_filtered else analysis.get("importance", 3),
            "reason":          analysis.get("reason", ""),
            "related_country": analysis.get("related_country", []),
        }
        analyzed.append(merged)

    # 중요도 내림차순 정렬
    analyzed.sort(key=lambda x: x.get("importance", 0), reverse=True)

    # 저장
    date_str = clean_path.stem.replace("clean_", "")
    out_path = ANALYZED_DIR / f"analyzed_{date_str}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(analyzed, f, ensure_ascii=False, indent=2)

    # 카테고리별 통계
    from collections import Counter
    cat_counts = Counter(a.get("category", "unknown") for a in analyzed)
    logger.info(f"카테고리별: {dict(cat_counts)}")
    logger.info(f"=== Analyzer 완료: {len(analyzed)}건 → {out_path} ===")
    return out_path


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else sorted(CLEAN_DIR.glob("clean_*.json"))[-1]
    run(path)
