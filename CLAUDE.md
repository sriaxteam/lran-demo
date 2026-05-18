# 이란전쟁 민생 이슈 발굴 에이전트 v2

수원시정연구원 | 28개 소스 | 미-이란전쟁(2026) → 수원시 민생 영향 자동 분석

## 파이프라인 구조

```
scheduler.py (07:00 / 19:00 자동 실행)
    └── orchestrator.py
            │
            ├── [Layer 1: 수집, 병렬]
            │     ├── collector.py           뉴스 9개 (Reuters·AP·BBC·AJ·연합뉴스·CSIS·Guardian·USNI·FT)
            │     ├── intl_org_collector.py  국제기구 6개 (IEA·IMF·OECD·WB·UNCTAD·OPEC)
            │     ├── kr_research_collector.py 연구기관 6개 (KEEI·KIEP·KDI·ChathamHouse·EU·METI)
            │     ├── domestic_tracker.py    국내공공 4개 (오피넷·통계청·가스·경기도)
            │     └── youtube_collector.py   유튜브 3채널 (주 3회: 월·수·금)
            │
            ├── [Layer 2: 정제]
            │     └── dedup.py
            │
            ├── [Layer 3: 분석 - Claude API]
            │     ├── analyzer.py            뉴스 분류·3줄 요약·중요도
            │     ├── paradigm_detector.py   패러다임 변화 신호 감지
            │     └── minseang_analyzer.py   수원시 민생 영향 + 정책 제언
            │
            └── [Layer 4: 출력]
                  └── reporter.py            HTML 5섹션 일일 브리핑
```

## 파일 구조

```
iran_news_agent/
├── CLAUDE.md
├── orchestrator.py
├── scheduler.py
├── config.py              ← API 키, 경로, 수원시 컨텍스트
│
├── [Layer 1 수집]
│   ├── collector.py
│   ├── intl_org_collector.py
│   ├── kr_research_collector.py
│   ├── domestic_tracker.py
│   ├── youtube_collector.py
│   ├── feeds.py           ← RSS URL 목록
│   └── sources.py         ← 스크래핑 대상
│
├── [Layer 2 정제]
│   └── dedup.py
│
├── [Layer 3 분석]
│   ├── analyzer.py
│   ├── paradigm_detector.py
│   └── minseang_analyzer.py
│
├── [Layer 4 출력]
│   └── reporter.py
│
├── data/
│   ├── raw/            뉴스 원본
│   ├── intl/           국제기구 발표
│   ├── research/       연구기관 보고서
│   ├── domestic/       국내 공공 지표
│   ├── youtube/        유튜브 자막 요약
│   ├── clean/          정제 완료
│   ├── analyzed/       분석 완료
│   ├── paradigm/       패러다임 신호
│   ├── policy/         민생분석·정책제언
│   └── reports/        최종 HTML 리포트
│
├── iran_news.db        SQLite 누적 DB
├── iran_agent.log      실행 로그
├── requirements.txt
└── .env                API 키 (Git 제외)
```

## 리포트 5개 섹션

| 섹션 | 내용 | 데이터 소스 |
|------|------|------------|
| 섹션 1 | 오늘의 전황 요약 | analyzer.py |
| 섹션 2 | 국내 물가·에너지 지표 | domestic_tracker.py |
| 섹션 3 | 수원시 민생 영향 분석 | minseang_analyzer.py |
| 섹션 4 | 패러다임 변화 신호 | paradigm_detector.py |
| 섹션 5 | 수원시 정책 제언 | minseang_analyzer.py |

## 실행 방법

```bash
# 즉시 1회 실행
python orchestrator.py

# 스케줄러 상시 실행
python scheduler.py

# 특정 날짜 재실행
python orchestrator.py --date 2026-04-16
```

## 환경 변수 (.env)

```
ANTHROPIC_API_KEY=sk-ant-...        # 필수
NEWSAPI_KEY=                         # 선택 (무료 100회/월)
GUARDIAN_API_KEY=                    # 선택 (무료 무제한)
NYT_API_KEY=                         # 선택 (무료 500회/일)
BRAVE_API_KEY=                       # 선택 (무료 2000회/월)
OPINET_API_KEY=                      # 선택 (무료, 오피넷 가입)
YOUTUBE_API_KEY=                     # 선택 (유튜브 자막 추출 보완용)
```

## 수원시 컨텍스트 (config.py 내장)

- 인구 약 119만 명 (경기도 최대)
- 삼성전자 본사 소재 → IT·제조업 협력사 에너지비 민감
- 취약계층: 기초수급·차상위·노인1인가구·외국인근로자
- 소상공인: 음식점·배달·운수업 에너지비 직격
- 재정자립도 약 40% → 경기도 매칭 사업 연계 중요
