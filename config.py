"""
config.py — 전체 설정
이란-미국 전쟁 민생 이슈 발굴 에이전트 v2 (28개 소스)
수원시정연구원
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR     = Path(__file__).parent
load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)
# IRAN_DATA_DIR 환경변수로 데이터 루트 전환 가능 (V2=data_v2)
DATA_DIR     = BASE_DIR / os.getenv("IRAN_DATA_DIR", "data")
RAW_DIR      = DATA_DIR / "raw"
CLEAN_DIR    = DATA_DIR / "clean"
ANALYZED_DIR = DATA_DIR / "analyzed"
REPORTS_DIR  = DATA_DIR / "reports"
INTL_DIR     = DATA_DIR / "intl"
RESEARCH_DIR = DATA_DIR / "research"
DOMESTIC_DIR = DATA_DIR / "domestic"
PARADIGM_DIR          = DATA_DIR / "paradigm"
POLICY_DIR            = DATA_DIR / "policy"
YT_DIR                = DATA_DIR / "youtube"
COUNTRY_RESPONSE_DIR  = DATA_DIR / "country_response"
DB_PATH      = BASE_DIR / "iran_news.db"
LOG_PATH     = BASE_DIR / "iran_agent.log"

for d in [RAW_DIR, CLEAN_DIR, ANALYZED_DIR, REPORTS_DIR,
          INTL_DIR, RESEARCH_DIR, DOMESTIC_DIR,
          PARADIGM_DIR, POLICY_DIR, YT_DIR, COUNTRY_RESPONSE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
NEWSAPI_KEY       = os.getenv("NEWSAPI_KEY", "")
GUARDIAN_API_KEY  = os.getenv("GUARDIAN_API_KEY", "")
NYT_API_KEY       = os.getenv("NYT_API_KEY", "")
BRAVE_API_KEY     = os.getenv("BRAVE_API_KEY", "")
OPINET_API_KEY    = os.getenv("OPINET_API_KEY", "")
KOSIS_API_KEY     = os.getenv("KOSIS_API_KEY", "")   # kosis.kr/openapi 무료 발급
YT_API_KEY        = os.getenv("YOUTUBE_API_KEY", "")

KEYWORDS_EN = [
    # ── 이란 직접 (단독 포함)
    "iran",
    "iran war", "iran us war", "hormuz", "hormuz blockade",
    "tehran", "irgc", "iranian", "iran ceasefire",
    "iran nuclear", "iran missile", "hezbollah iran",
    "strait of hormuz", "iran oil", "iran blockade",
    "iran sanction", "iran attack", "iran deal",
    # ── 중동 지역 정세
    "middle east war", "middle east conflict", "persian gulf",
    "gulf crisis", "red sea", "houthi", "hezbollah",
    "israel iran", "israel strike", "israel war",
    "gaza war", "west bank", "hamas",
    # ── 에너지·유가 (간접 영향)
    "oil price", "crude oil", "oil market", "opec cut",
    "energy crisis", "energy security", "oil supply",
    "lng price", "gas price spike", "fuel price",
    "oil sanction", "energy sanction",
    # ── 경제·공급망 (간접 영향)
    "shipping disruption", "suez canal", "supply chain",
    "tanker attack", "naval blockade", "oil tanker",
    "global inflation", "war economy",
]
KEYWORDS_KO = [
    # ── 이란 직접 (단독 포함 — 제목에 "이란"만 있어도 수집)
    "이란",
    "이란 전쟁", "이란 미국", "호르무즈", "이란 핵",
    "이란 봉쇄", "테헤란", "이란 휴전", "이란전", "이란 공격",
    # ── 중동 지역 (단독 포함)
    "중동", "걸프",
    "중동전쟁", "중동 분쟁", "페르시아만", "홍해", "후티",
    "헤즈볼라", "이스라엘 이란", "가자", "하마스",
    # ── 원전·에너지 시설
    "원전 폭격", "원전 공격", "부셰르", "바라카",
    # ── 에너지·유가
    "유가", "원유", "에너지 위기", "에너지 안보",
    "유류비", "난방비", "도시가스", "LNG 가격",
    # ── 경제·물가
    "물가", "인플레", "공급망", "해운 운임",
    # ── 한국 부처 대응 (이란·중동 사태 관련 정부 발표 수집용)
    "외교부 이란", "외교부 중동", "산업부 에너지", "산업부 LNG",
    "기재부 유가", "기재부 물가", "기재부 비상", "유류세 인하",
    "식약처 원료", "식약처 수급", "농림부 곡물", "농림부 식량",
    "에너지 비상대책", "에너지 수급 비상", "LNG 수입 다변화",
    "에너지 긴급", "원유 비축", "전략비축유", "수입 다변화",
    "중동 사태 대응", "에너지 대응", "정부 긴급 대책",
]
KEYWORDS_MINSEANG_KO = [
    "유가", "물가", "에너지", "난방비", "전기료", "도시가스",
    "소상공인", "민생", "장바구니", "생활비", "인플레",
    "수원시", "경기도", "취약계층",
]
PARADIGM_KEYWORDS = [
    "energy security", "energy transition", "supply diversification",
    "strategic reserve", "energy partnership", "reliability",
    "recession", "growth forecast", "inflation outlook",
    "trade disruption", "supply chain", "shipping route",
    "price cap", "export controls", "hoarding", "emergency",
    "paradigm", "fragmentation", "geopolitical", "decoupling",
    "에너지안보", "패러다임", "공급망재편", "무역질서",
]

ISSUE_CATEGORIES = [
    "military", "diplomacy", "energy", "economy",
    "humanitarian", "nuclear", "korea", "paradigm",
    "country_response",   # 각국 대응 방안 (미·중·러·EU·사우디 등)
]

# ── 각국 대응 추적 대상 국가·세력
TREND_COUNTRIES = [
    "미국", "이스라엘", "사우디아라비아", "UAE", "카타르",
    "중국", "러시아", "EU", "영국", "한국", "일본", "인도",
    "튀르키예", "파키스탄", "이라크", "시리아",
]

# ── 한국 중앙정부 부처별 대응 추적 대상
KR_MINISTRIES = [
    "외교부", "산업부", "기재부", "국토부", "기후에너지부",
    "식약처", "농림부",
]

SUWON_CONTEXT = """
수원시 기본 정보:
- 인구: 약 119만 명 (경기도 최대 도시)
- 주요 산업: 삼성전자 본사 소재, IT·제조업 중심
- 에너지: 도시가스·전기 의존, 중동산 LNG 간접 영향
- 취약계층: 기초생활수급자·차상위·노인1인가구·외국인근로자
- 소상공인: 음식점·배달·운수업 에너지비 민감
- 재정자립도: 약 40% (경기도 지원사업 연계 중요)
"""

YOUTUBE_CHANNELS = {
    "AlJazeera_EN": {
        "channel_id": "UCNye-wNBqNL5ZzHSJj3l8Bg",
        "name": "Al Jazeera English",
        "lang": "en", "credibility": 8.0,
    },
    "DW_News": {
        "channel_id": "UCknLrEdhRCp1aegoMqRaCZg",
        "name": "DW News",
        "lang": "en", "credibility": 8.5,
    },
    "Yonhap_TV": {
        "channel_id": "UCTHCOPwqNfZ0uiKOvFyhGwg",
        "name": "연합뉴스TV",
        "lang": "ko", "credibility": 8.0,
    },
}
YOUTUBE_SCHEDULE_DAYS = [0, 3]   # 월요일(0), 목요일(3) — 주 2회 발행

CLAUDE_MODEL        = "claude-sonnet-4-5-20250929"
ANALYZER_MODEL      = "claude-haiku-4-5"          # Analyzer 전용 (비용 절감)
ANALYZER_BATCH_SIZE = 20                            # 배치 크기 10→20 (API 호출 횟수 절반)
REQUEST_DELAY       = 2.0
SCHEDULE_TIMES      = ["07:00", "19:00"]
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
