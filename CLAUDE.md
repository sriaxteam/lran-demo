# 이란전쟁 민생 이슈 발굴 에이전트 v2

수원시정연구원 | 28개 소스 | 미-이란전쟁(2026) → 수원시 민생 영향 자동 분석

> **v2 독립 레포**: https://github.com/bora01194845421-hub/lran-v2
> **v1 안정 레포**: https://github.com/bora01194845421-hub/lran
> **대시보드 포트**: 8503 (v1은 8502)
> **데이터 루트**: data_v2/ (환경변수 IRAN_DATA_DIR=data_v2)

## 실행 방법

```bash
streamlit run dashboard.py --server.port 8503
python orchestrator.py
python orchestrator.py --date 2026-05-19
python scheduler.py
```

## 환경 변수 (.env)

```
ANTHROPIC_API_KEY=sk-ant-...
NEWSAPI_KEY=
GUARDIAN_API_KEY=
NYT_API_KEY=
BRAVE_API_KEY=
OPINET_API_KEY=
YOUTUBE_API_KEY=
IRAN_DATA_DIR=data_v2
```
