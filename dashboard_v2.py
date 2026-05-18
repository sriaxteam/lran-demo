"""
이란전쟁 민생 브리핑 대시보드 — V2 수동입력
수원시정연구원

- 데이터 소스: data_v2/ (엑셀 직접 제공)
- 분석 실행:  python manual_input.py --file 파일.xlsx

실행:
  python -m streamlit run dashboard_v2.py --server.address 0.0.0.0 --server.port 8503
"""

import os

# V2 환경 설정 — config.py import 전에 반드시 먼저 설정
os.environ["IRAN_DATA_DIR"]     = "data_v2"
os.environ["IRAN_DASH_VERSION"] = "V2"

import runpy
from pathlib import Path

runpy.run_path(
    str(Path(__file__).parent / "dashboard.py"),
    run_name="__main__",
)
