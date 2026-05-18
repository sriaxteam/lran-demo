import json, sys
sys.stdout.reconfigure(encoding="utf-8")

BASE = r"C:\Users\user\Desktop\iran_news_agent_final\iran_final\data"

# minseang
d = json.load(open(BASE + r"\policy\minseang_20260427.json", encoding="utf-8"))
print(f"[minseang]")
print(f"  urgency   : {d.get('urgency')}")
print(f"  headline  : {d.get('today_headline','')[:60]}")
print(f"  민생분석 키: {list(d.get('민생경제_분석', {}).keys())}")
print(f"  대응과제 수: {len(d.get('우선_대응과제', []))}")
if "error" in d:
    print(f"  ERROR: {d['error'][:80]}")

# paradigm
d = json.load(open(BASE + r"\paradigm\paradigm_20260427.json", encoding="utf-8"))
print(f"\n[paradigm]")
print(f"  total_signals    : {d.get('total_signals')}")
print(f"  structural_signals: {d.get('structural_signals')}")

# country_response
d = json.load(open(BASE + r"\country_response\cr_20260427.json", encoding="utf-8"))
print(f"\n[country_response]")
print(f"  country_responses: {len(d.get('country_responses', []))}")
print(f"  emerging_issues  : {len(d.get('emerging_issues', []))}")
if "error" in d:
    print(f"  ERROR: {d['error'][:80]}")
