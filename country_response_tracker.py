"""
Country Response Tracker
각국·세력의 대응 방안 추적 + 이슈 발굴 에이전트

입력:
  - data/analyzed/analyzed_YYYYMMDD.json     (일반 뉴스 분석)
  - data/intl/intl_YYYYMMDD.json             (국제기구 발표)
  - data/research/research_YYYYMMDD.json     (연구기관·싱크탱크)

처리 (Claude API):
  1. 각국 대응 방안 매트릭스
     — 포지션·구체 행동·향후 전망·수원시 연결점
  2. 이슈 발굴
     — 아직 헤드라인 아니지만 중요해질 이슈
     — 왜 중요한지·주목 포인트·예상 전개 시점
  3. 핵심 동향 요약 (3~5줄)

출력: data/country_response/cr_YYYYMMDD.json
{
  "date": "2026-04-17",
  "country_responses": [
    {
      "country": "중국",
      "stance": "전략적 중립 유지하며 중재 모색",
      "actions": ["왕이 테헤란·워싱턴 접촉", "호르무즈 봉쇄 해제 촉구"],
      "policy_direction": "에너지 확보 및 중재자 역할 강화",
      "outlook": "중장기적 중동 영향력 확대 시도",
      "suwon_relevance": "한-중 무역 및 삼성 공급망에 간접 영향"
    }
  ],
  "emerging_issues": [
    {
      "issue": "파키스탄 핵 억제력 활성화 우려",
      "why_important": "역내 핵 확산 가능성으로 전쟁 확산 리스크",
      "watch_for": "파키스탄-이란 국경 긴장, 미-파 외교 접촉",
      "timeline": "중기(1개월)",
      "suwon_relevance": "에너지 위기 장기화 시 수원시 에너지 비용 상승"
    }
  ],
  "key_trends": ["동향1", "동향2", "동향3"],
  "summary_ko": "오늘 각국 대응 요약"
}
"""

import json
import logging
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import anthropic

from config import (
    ANTHROPIC_API_KEY, CLAUDE_MODEL,
    ANALYZED_DIR, COUNTRY_RESPONSE_DIR,
    DATA_DIR, TREND_COUNTRIES, KR_MINISTRIES, SUWON_CONTEXT,
)

logger = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

INTL_DIR     = DATA_DIR / "intl"
RESEARCH_DIR = DATA_DIR / "research"

# ─────────────────────────────────────────────
# 시스템 프롬프트
# ─────────────────────────────────────────────

SYSTEM_PROMPT = f"""당신은 수원시정연구원의 국제정세·민생정책 전문 분석가입니다.
이란-미국 전쟁(2026)에 대한 각국·세력의 대응 방안을 추적하고,
아직 주목받지 못한 중요 이슈를 발굴합니다.

{SUWON_CONTEXT}

반드시 JSON 형식으로만 응답하세요. 마크다운 코드블록 없이 순수 JSON만 출력하세요."""

TRACKER_PROMPT = """다음은 오늘({date}) 수집된 이란-미국 전쟁 관련 뉴스·보고서 {total}건입니다.

기사 데이터:
{articles_json}

아래 4가지를 분석해서 JSON으로 반환하세요.

━━ 분석 과제 ━━

1. country_responses — 각국·세력의 대응 방안 매트릭스
   분석 대상: {countries}
   조건: 오늘 뉴스에 근거가 있는 국가만 포함 (근거 없으면 제외)
   필드:
   · country: 국가·세력 이름
   · stance: 현재 포지션 한 줄 요약
   · actions: 구체적 행동·조치 (최대 3개)
   · policy_direction: 정책 방향성 한 줄
   · outlook: 향후 1~2주 전망 한 줄
   · suwon_relevance: 수원시 민생·경제와의 연결점 (없으면 빈 문자열)

2. kr_ministry_responses — 한국 중앙정부 부처별 대응 매트릭스
   분석 대상: {ministries}
   작성 기준 (2단계):
   · [확인] 오늘 뉴스에서 해당 부처의 실제 발표·조치·입장이 확인된 경우
   · [예상] 뉴스 근거 없어도 전쟁 상황·부처 소관 업무상 당연히 취해야 할 조치
     → 예: 산업부=LNG 수급, 기재부=유류세·물가, 농림부=곡물비축, 식약처=의약품원료
   · 반드시 {ministries} 전체 부처를 포함할 것 (하나도 빠뜨리지 말 것)
   · confirmed 필드로 뉴스 확인 여부를 구분
   필드:
   · ministry: 부처명 (예: "외교부", "산업부", "기재부", "국토부", "기후에너지부", "식약처", "농림부")
   · confirmed: true(뉴스 확인) / false(상황 기반 예상)
   · stance: 현재 입장·대응 방향 한 줄 요약
   · actions: 구체적 발표·조치 또는 예상 조치 (최대 3개)
   · policy_direction: 정책 방향성 한 줄
   · suwon_relevance: 수원시 민생·경제와의 연결점 (없으면 빈 문자열)

3. emerging_issues — 이슈 발굴
   기준: 아직 헤드라인은 아니지만 향후 중요해질 이슈
   필드:
   · issue: 이슈 제목 (20자 이내)
   · why_important: 왜 중요한가 (2줄 이내)
   · watch_for: 무엇을 주목해야 하나 (1줄)
   · timeline: "단기(1주)" / "중기(1개월)" / "장기(3개월+)" 중 하나
   · suwon_relevance: 수원시 민생·정책 연결점 (없으면 빈 문자열)

4. key_trends — 오늘 각국 대응 흐름에서 포착된 핵심 동향 (3~5개, 한 문장씩)

━━ 반환 형식 ━━
{{
  "date": "{date}",
  "country_responses": [
    {{
      "country": "국가명",
      "stance": "포지션 한 줄",
      "actions": ["행동1", "행동2"],
      "policy_direction": "정책 방향성",
      "outlook": "향후 전망",
      "suwon_relevance": "수원시 연결점"
    }}
  ],
  "kr_ministry_responses": [
    {{
      "ministry": "부처명",
      "confirmed": true,
      "stance": "입장·대응 방향 한 줄",
      "actions": ["조치1", "조치2", "조치3"],
      "policy_direction": "정책 방향성",
      "suwon_relevance": "수원시 연결점"
    }}
  ],
  "⚠️주의": "kr_ministry_responses에는 {ministries}의 모든 부처가 반드시 포함되어야 합니다.",
  "emerging_issues": [
    {{
      "issue": "이슈 제목",
      "why_important": "왜 중요한가",
      "watch_for": "주목 포인트",
      "timeline": "단기(1주)",
      "suwon_relevance": "수원시 연결점"
    }}
  ],
  "key_trends": ["동향1", "동향2", "동향3"],
  "summary_ko": "오늘 각국 대응 및 이슈 발굴 전체 요약 (3줄 이내, 각 줄 • 시작, \\n 구분)"
}}"""


# ─────────────────────────────────────────────
# 데이터 로드
# ─────────────────────────────────────────────

def load_articles(date_str: str, max_items: int = 60) -> list:
    """3개 소스에서 기사 로드, 중요도 순 정렬.
    한국 부처 관련 기사(korea 카테고리 또는 related_country에 한국 포함)는
    중요도와 무관하게 최대 15건 우선 포함 보장."""
    all_items = []
    kr_ministry_kw = ["외교부", "산업부", "산업통상자원부", "기재부", "기획재정부",
                      "국토부", "국토교통부", "식약처", "식품의약품안전처",
                      "농림부", "농림축산식품부", "기후에너지부"]

    # 1. 일반 뉴스 (중요도 3 이상)
    analyzed_path = ANALYZED_DIR / f"analyzed_{date_str}.json"
    if analyzed_path.exists():
        with open(analyzed_path, encoding="utf-8") as f:
            data = json.load(f)
        # 1-a. 한국 부처 기사 — 중요도 무관 우선 확보 (최대 15건)
        kr_ministry_items = [
            a for a in data
            if (a.get("category") == "korea" or "한국" in a.get("related_country", []))
            and any(kw in (a.get("title", "") + a.get("summary_ko", ""))
                    for kw in kr_ministry_kw)
        ][:15]
        # 1-b. 나머지 중요도 3 이상 기사
        kr_ids = {a.get("id") for a in kr_ministry_items}
        filtered = [a for a in data
                    if a.get("importance", 0) >= 3 and a.get("id") not in kr_ids]
        all_items.extend(kr_ministry_items)
        all_items.extend(filtered)
        logger.info(f"일반 뉴스: {len(filtered)}건 + 한국부처: {len(kr_ministry_items)}건 로드")

    # 2. 국제기구 발표
    intl_path = INTL_DIR / f"intl_{date_str}.json"
    if intl_path.exists():
        with open(intl_path, encoding="utf-8") as f:
            data = json.load(f)
        all_items.extend(data)
        logger.info(f"국제기구: {len(data)}건 로드")

    # 3. 연구기관·싱크탱크
    research_path = RESEARCH_DIR / f"research_{date_str}.json"
    if research_path.exists():
        with open(research_path, encoding="utf-8") as f:
            data = json.load(f)
        all_items.extend(data)
        logger.info(f"연구기관: {len(data)}건 로드")

    # 중요도 내림차순 정렬, 최대 max_items 선택
    all_items.sort(key=lambda x: x.get("importance", 0), reverse=True)
    return all_items[:max_items]


def build_prompt_articles(articles: list) -> str:
    """Claude 프롬프트용 기사 요약 JSON 생성"""
    summaries = []
    for a in articles:
        summaries.append({
            "title":           a.get("title", ""),
            "source":          a.get("source", ""),
            "category":        a.get("category", ""),
            "summary_ko":      a.get("summary_ko", "")[:150],
            "keywords":        a.get("keywords", [])[:5],
            "related_country": a.get("related_country", []),
            "importance":      a.get("importance", 3),
            "org_type":        a.get("org_type", ""),
        })
    return json.dumps(summaries, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────
# Claude API 호출
# ─────────────────────────────────────────────

def track_with_claude(articles: list, report_date: str) -> dict:
    prompt = TRACKER_PROMPT.format(
        date=report_date,
        total=len(articles),
        articles_json=build_prompt_articles(articles),
        countries=", ".join(TREND_COUNTRIES),
        ministries=", ".join(KR_MINISTRIES),
    )

    try:
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=8096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)

        logger.info(
            f"각국 대응 {len(result.get('country_responses', []))}개 | "
            f"이슈 발굴 {len(result.get('emerging_issues', []))}개 | "
            f"동향 {len(result.get('key_trends', []))}개"
        )
        return result

    except json.JSONDecodeError as e:
        logger.warning(f"[CountryTracker] JSON 파싱 실패: {e}")
        return {"date": report_date, "error": str(e)}
    except Exception as e:
        logger.warning(f"[CountryTracker] Claude API 실패: {e}")
        return {"date": report_date, "error": str(e)}


# ─────────────────────────────────────────────
# 통계 로그
# ─────────────────────────────────────────────

def log_stats(result: dict):
    """국가별 포지션 분포 로그"""
    responses = result.get("country_responses", [])
    if responses:
        countries = [r["country"] for r in responses]
        logger.info(f"추적 국가: {', '.join(countries)}")

    issues = result.get("emerging_issues", [])
    if issues:
        timelines = defaultdict(int)
        for i in issues:
            timelines[i.get("timeline", "미분류")] += 1
        logger.info(f"이슈 발굴 타임라인: {dict(timelines)}")


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────

def run(target_date: str = None) -> Path:
    if target_date is None:
        target_date = date.today().strftime("%Y-%m-%d")

    date_str = target_date.replace("-", "")
    logger.info(f"=== CountryResponseTracker 시작: {target_date} ===")

    # 기사 로드
    articles = load_articles(date_str)

    if not articles:
        logger.warning("분석할 기사 없음 — CountryResponseTracker 건너뜀")
        empty = {
            "date": target_date,
            "country_responses": [],
            "emerging_issues": [],
            "key_trends": [],
            "summary_ko": "• 오늘은 각국 대응 관련 기사가 수집되지 않았습니다.",
            "generated_at": datetime.utcnow().isoformat(),
        }
        out_path = COUNTRY_RESPONSE_DIR / f"cr_{date_str}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(empty, f, ensure_ascii=False, indent=2)
        return out_path

    # Claude API 분석
    logger.info(f"Claude API 분석 중 ({len(articles)}건)...")
    result = track_with_claude(articles, target_date)

    # 통계 로그
    log_stats(result)

    # 메타데이터 추가
    result["generated_at"] = datetime.utcnow().isoformat()
    result["articles_analyzed"] = len(articles)

    # 저장
    out_path = COUNTRY_RESPONSE_DIR / f"cr_{date_str}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    logger.info(f"=== CountryResponseTracker 완료 → {out_path} ===")
    return out_path


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    run(sys.argv[1] if len(sys.argv) > 1 else None)
