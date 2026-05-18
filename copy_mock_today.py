"""
오늘 날짜 목업 데이터 복사 스크립트
20260420 데이터를 오늘 날짜로 복사
"""
import json, sys
from pathlib import Path
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).parent / "data"
SRC  = "20260420"
DST  = date.today().strftime("%Y%m%d")
today_str = date.today().strftime("%Y-%m-%d")

pairs = [
    (BASE / "analyzed"         / f"analyzed_{SRC}.json",   BASE / "analyzed"         / f"analyzed_{DST}.json"),
    (BASE / "clean"            / f"clean_{SRC}.json",      BASE / "clean"            / f"clean_{DST}.json"),
    (BASE / "country_response" / f"cr_{SRC}.json",         BASE / "country_response" / f"cr_{DST}.json"),
    (BASE / "domestic"         / f"domestic_{SRC}.json",   BASE / "domestic"         / f"domestic_{DST}.json"),
    (BASE / "paradigm"         / f"paradigm_{SRC}.json",   BASE / "paradigm"         / f"paradigm_{DST}.json"),
    (BASE / "policy"           / f"minseang_{SRC}.json",   BASE / "policy"           / f"minseang_{DST}.json"),
    (BASE / "youtube"          / f"yt_summary_{SRC}.json", BASE / "youtube"          / f"yt_summary_{DST}.json"),
]

for src, dst in pairs:
    if src.exists() and not dst.exists():
        data = json.loads(src.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            if "date" in data:
                data["date"] = today_str
            if "generated_at" in data:
                data["generated_at"] = today_str + "T07:00:00.000000"
        dst.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  OK  복사 완료: {dst.name}")
    elif dst.exists():
        print(f"  --  이미 존재: {dst.name}")
    else:
        print(f"  ??  소스 없음: {src.name}")

print(f"\n대상 날짜: {DST}")
print("완료! 대시보드를 새로고침하세요.")
