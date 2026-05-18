"""
Minseang Analyzer (수원시 민생 영향 분석기)
Claude API로 수원시 민생 영향 분석 + 정책 제언 생성

입력: analyzed, domestic, paradigm, yt_summary JSON
출력: data/policy/minseang_YYYYMMDD.json
"""
import json, logging
from datetime import date, datetime
from pathlib import Path
import anthropic
from config import (
    ANTHROPIC_API_KEY, CLAUDE_MODEL, POLICY_DIR,
    ANALYZED_DIR, DOMESTIC_DIR, PARADIGM_DIR, YT_DIR, SUWON_CONTEXT
)
logger = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM = f"""당신은 수원시정연구원의 민생정책 전문 분석가입니다.
이란-미국 전쟁(2026)이 수원시 시민 생활에 미치는 영향을 분석하고
수원시가 취할 수 있는 민생안정 정책을 제언합니다.

{SUWON_CONTEXT}

반드시 JSON 형식만 반환하세요."""

PROMPT = """오늘 수집된 다음 데이터를 종합해서 수원시 민생경제 분석과 우선 대응과제를 JSON으로 작성하세요.

[국제 전황 요약 — 오늘 수집 핵심 기사]
{war_summary}

[국내 물가·에너지 지표]
{domestic_summary}

[패러다임 변화 신호]
{paradigm_summary}

[유튜브·전문가 브리핑 요약]
{yt_summary}

[지난주 분석 결과 — 중복 지양, 변화·심화·신규 이슈 중심으로 작성]
{prev_summary}

⚠️ 작성 지침:
1. 지난주와 동일한 제목·내용 반복 금지 — 반드시 이번주 새로운 데이터·사건·수치를 근거로 작성
2. 이번주 핵심 신규 사항(호르무즈 선박 억류 구체화, IEA 비축유 방출, 6월 도시가스 인상 임박, IMF 패러다임 전환 선언 등)을 반드시 반영
3. 전문가_의견은 유튜브 브리핑 실제 내용을 구체적으로 인용할 것
4. 수치·지표는 오늘 날짜 기준 최신값 사용
5. 지난주 우선과제 제목이 이번주에 그대로 반복되면 안 됨 — 제목부터 완전히 새로운 표현 사용
6. 지난주 다음주 주목이슈에 예고된 사건들(6월 도시가스 인상, 삼성 실적 등)의 실제 진행 상황과 수원시 영향을 이번주 내용에 구체적으로 반영

반환 형식:
{{
  "민생경제_분석": {{
    "지역산업": {{
      "level": "높음|중간|낮음|모니터링",
      "summary": "수원시 지역산업(삼성전자·제조업·수출기업) 영향 분석 2~3줄",
      "key_indicator": "핵심 지표 또는 수치 1줄",
      "타지자체_현황": "유사 산업구조 타 지자체(예: 화성·평택·인천) 대응 현황 1~2줄"
    }},
    "소상공인_자영업": {{
      "level": "높음|중간|낮음|모니터링",
      "summary": "수원시 소상공인·자영업(음식점·배달·운수·유류비) 영향 분석 2~3줄",
      "key_indicator": "핵심 지표 또는 수치 1줄",
      "타지자체_현황": "소상공인 지원 선도 타 지자체(예: 전주·서울) 대응 현황 1~2줄"
    }},
    "시민생활": {{
      "level": "높음|중간|낮음|모니터링",
      "summary": "수원시 시민생활(도시가스·전기료·물가·취약계층) 영향 분석 2~3줄",
      "key_indicator": "핵심 지표 또는 수치 1줄",
      "타지자체_현황": "에너지복지 선도 타 지자체(예: 서울·경기도) 대응 현황 1~2줄"
    }}
  }},
  "우선_대응과제": [
    {{
      "순위": 1,
      "title": "대응과제 제목 (간결하게)",
      "description": "과제 내용 및 기대효과 2~3줄",
      "priority": "즉시|단기|중기",
      "근거": {{
        "타지자체_벤치마킹": "어느 지자체의 어떤 사례를 참고했는가",
        "전문가_의견": "유튜브·전문가 브리핑에서 언급된 관련 내용",
        "보고서_근거": "KEEI·KIEP·KDI·IEA 등 보고서 인용 근거"
      }}
    }},
    {{
      "순위": 2,
      "title": "대응과제 제목",
      "description": "과제 내용 및 기대효과 2~3줄",
      "priority": "즉시|단기|중기",
      "근거": {{
        "타지자체_벤치마킹": "벤치마킹 사례",
        "전문가_의견": "전문가 의견",
        "보고서_근거": "보고서 인용"
      }}
    }},
    {{
      "순위": 3,
      "title": "대응과제 제목",
      "description": "과제 내용 및 기대효과 2~3줄",
      "priority": "즉시|단기|중기",
      "근거": {{
        "타지자체_벤치마킹": "벤치마킹 사례",
        "전문가_의견": "전문가 의견",
        "보고서_근거": "보고서 인용"
      }}
    }}
  ],
  "today_headline": "오늘 수원시가 가장 주목해야 할 민생 이슈 한 줄",
  "urgency": "긴급|주의|모니터링",
  "scout_points": [
    "전황 요약 포인트 1 (수원시 민생 연결 중심)",
    "전황 요약 포인트 2",
    "전황 요약 포인트 3"
  ],
  "next_week_issues": [
    {{
      "title": "다음주 주목할 이슈 제목 1",
      "detail": "수원시 민생에 미치는 영향 및 모니터링 포인트 2~3줄",
      "tag": "고위험",
      "tag_cls": "ni-high"
    }},
    {{
      "title": "다음주 주목할 이슈 제목 2",
      "detail": "수원시 민생에 미치는 영향 및 모니터링 포인트 2~3줄",
      "tag": "주목",
      "tag_cls": "ni-mid"
    }},
    {{
      "title": "다음주 주목할 이슈 제목 3",
      "detail": "수원시 민생에 미치는 영향 및 모니터링 포인트 2~3줄",
      "tag": "확인 필요",
      "tag_cls": "ni-watch"
    }},
    {{
      "title": "다음주 주목할 이슈 제목 4",
      "detail": "수원시 민생에 미치는 영향 및 모니터링 포인트 2~3줄",
      "tag": "모니터링",
      "tag_cls": "ni-watch"
    }}
  ],
  "lga_responses": [
    {{
      "name": "경기도",
      "type": "도",
      "stage": "선제|적극|검토|모니터링",
      "actions": "오늘 전황·지표 기반으로 경기도가 취하고 있거나 취해야 할 구체적 조치",
      "ref": "수원시와 연계 가능한 사업 또는 벤치마킹 포인트"
    }},
    {{
      "name": "서울특별시",
      "type": "광역",
      "stage": "선제|적극|검토|모니터링",
      "actions": "오늘 전황·지표 기반으로 서울시 관련 대응 현황 또는 제언",
      "ref": "수원시 적용 가능 모델"
    }},
    {{
      "name": "인천광역시",
      "type": "광역",
      "stage": "선제|적극|검토|모니터링",
      "actions": "인천시 항만·물류 관련 에너지 대응 현황",
      "ref": "수원시 연계 포인트"
    }},
    {{
      "name": "전주시",
      "type": "기초",
      "stage": "선제|적극|검토|모니터링",
      "actions": "소상공인·에너지 복지 관련 전주시 선도 사례",
      "ref": "수원시 직접 적용 가능 여부"
    }},
    {{
      "name": "화성시",
      "type": "기초",
      "stage": "선제|적극|검토|모니터링",
      "actions": "반도체·제조업 협력업체 관련 화성시 대응",
      "ref": "삼성전자 협력업체 공동 대응 가능성"
    }}
  ]
}}"""


def load_summary(path: Path, max_items: int = 5) -> str:
    if not path or not path.exists():
        return "데이터 없음"
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            # 중요도 높은 기사 우선 정렬
            if data and "importance" in data[0]:
                data = sorted(data, key=lambda x: x.get("importance", 0), reverse=True)
            items = data[:max_items]
            return "\n".join(f"- [{a.get('source','')}] {a.get('title','')} | {a.get('summary_ko','')[:120]}" for a in items)
        elif isinstance(data, dict):
            return json.dumps(data, ensure_ascii=False)[:2000]
    except Exception:
        return "로드 실패"
    return ""


def load_prev_summary(policy_dir: Path, current_date_str: str) -> str:
    """지난주 minseang 데이터 로드 — 차별화를 위해 상세 컨텍스트 전달"""
    files = sorted(policy_dir.glob("minseang_*.json"), reverse=True)
    for f in files:
        if f.stem.replace("minseang_", "") < current_date_str:
            try:
                data = json.load(open(f, encoding="utf-8"))
                headline   = data.get("today_headline", "")
                urgency    = data.get("urgency", "")
                tasks      = data.get("우선_대응과제", [])
                ni_issues  = data.get("next_week_issues", [])
                eco        = data.get("민생경제_분석", {})
                lga        = data.get("lga_responses", [])

                task_lines = [
                    f'  {t["순위"]}. [{t.get("priority","")}] {t["title"]} — {t.get("description","")[:60]}'
                    for t in tasks
                ]
                ni_lines = [f'  - {n["title"]}' for n in ni_issues]
                eco_lines = []
                for k, v in eco.items():
                    if isinstance(v, dict):
                        eco_lines.append(f'  {k}: {v.get("key_indicator","")}')
                lga_lines = [f'  {l["name"]}({l.get("stage","")}): {l.get("actions","")[:50]}' for l in lga]

                parts = [
                    f"[지난주 날짜] {data.get('date','')} | 긴급도: {urgency}",
                    f"[지난주 헤드라인] {headline}",
                    f"[지난주 우선과제 — 이번주 반드시 다른 제목·내용으로 작성]",
                ] + task_lines + [
                    f"[지난주 다음주 주목이슈 — 이번주 이 이슈들의 후속·변화·심화를 다룰 것]",
                ] + ni_lines + [
                    f"[지난주 핵심 지표]",
                ] + eco_lines + [
                    f"[지난주 지자체 대응 단계 — 이번주 진전·변화 중심으로]",
                ] + lga_lines

                return "\n".join(parts)
            except Exception:
                continue
    return "이전 데이터 없음"


def run(target_date: str = None) -> Path:
    if target_date is None:
        target_date = date.today().strftime("%Y-%m-%d")
    date_str = target_date.replace("-", "")
    logger.info(f"=== MinseangAnalyzer 시작: {target_date} ===")

    analyzed_path = ANALYZED_DIR / f"analyzed_{date_str}.json"
    domestic_path = DOMESTIC_DIR / f"domestic_{date_str}.json"
    paradigm_path = PARADIGM_DIR / f"paradigm_{date_str}.json"
    yt_path       = YT_DIR / f"yt_summary_{date_str}.json"

    prompt = PROMPT.format(
        war_summary     = load_summary(analyzed_path, max_items=20),  # 상위 20건
        domestic_summary= load_summary(domestic_path),
        paradigm_summary= load_summary(paradigm_path),
        yt_summary      = load_summary(yt_path),
        prev_summary    = load_prev_summary(POLICY_DIR, date_str),
    )

    try:
        resp = client.messages.create(
            model=CLAUDE_MODEL, max_tokens=8096,
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip().replace("```json","").replace("```","").strip()
        result = json.loads(raw)
    except Exception as e:
        logger.warning(f"Claude 실패: {e}")
        result = {"error": str(e), "today_headline": "분석 실패", "urgency": "모니터링"}

    result["date"] = target_date
    result["generated_at"] = datetime.utcnow().isoformat()

    out_path = POLICY_DIR / f"minseang_{date_str}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    logger.info(f"긴급도: {result.get('urgency')} | 헤드라인: {result.get('today_headline','')}")
    logger.info(f"=== MinseangAnalyzer 완료 → {out_path} ===")
    return out_path


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    run(sys.argv[1] if len(sys.argv) > 1 else None)
