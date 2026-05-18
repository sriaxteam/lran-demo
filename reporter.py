"""
Reporter — 일일 HTML 브리핑 생성 (5개 섹션)

섹션 1: 오늘의 전황 요약 (군사·외교·에너지·경제)
섹션 2: 오늘의 국내 지표 (유가·물가·에너지)
섹션 3: 수원시 민생 영향 분석
섹션 4: 패러다임 변화 신호
섹션 5: 수원시 정책 제언 + 타 지자체·국외 사례

출력: data/reports/report_YYYYMMDD.html
"""
import json, logging, sqlite3
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from config import (
    ANALYZED_DIR, DOMESTIC_DIR, PARADIGM_DIR,
    POLICY_DIR, YT_DIR, REPORTS_DIR, DB_PATH,
    ISSUE_CATEGORIES, DATA_DIR,
)
COUNTRY_RESPONSE_DIR = DATA_DIR / "country_response"
logger = logging.getLogger(__name__)

CAT_KO = {
    "military":"군사","diplomacy":"외교·협상","energy":"에너지·호르무즈",
    "economy":"경제·금융","humanitarian":"인도주의","nuclear":"핵",
    "korea":"한국 영향","paradigm":"패러다임 변화","unknown":"기타"
}
CAT_COLOR = {
    "military":"#FCEBEB","diplomacy":"#E6F1FB","energy":"#FAEEDA",
    "economy":"#E1F5EE","humanitarian":"#FBEAF0","nuclear":"#EEEDFE",
    "korea":"#EAF3DE","paradigm":"#E8EAF6","unknown":"#F1EFE8"
}
CAT_TEXT = {
    "military":"#A32D2D","diplomacy":"#185FA5","energy":"#854F0B",
    "economy":"#085041","humanitarian":"#72243E","nuclear":"#3C3489",
    "korea":"#27500A","paradigm":"#283593","unknown":"#5F5E5A"
}
RISK_COLOR = {"높음":"#FCEBEB","중간":"#FAEEDA","낮음":"#E1F5EE","모니터링":"#F1EFE8"}
RISK_TEXT  = {"높음":"#A32D2D","중간":"#854F0B","낮음":"#085041","모니터링":"#5F5E5A"}


def load_json(path: Path):
    if path and path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def build_section1(analyzed: list) -> str:
    if not analyzed:
        return "<p style='color:#9CA3AF;font-size:13px;'>수집된 기사 없음</p>"
    by_cat = defaultdict(list)
    for a in analyzed:
        by_cat[a.get("category","unknown")].append(a)
    html = ""
    for cat in ISSUE_CATEGORIES:
        items = by_cat.get(cat, [])
        if not items:
            continue
        bg = CAT_COLOR.get(cat,"#F1EFE8")
        tc = CAT_TEXT.get(cat,"#5F5E5A")
        html += f"""
        <div style="margin-bottom:16px;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <span style="font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px;background:{bg};color:{tc};">{CAT_KO.get(cat,cat)}</span>
            <span style="font-size:11px;color:#9CA3AF;">{len(items)}건</span>
          </div>"""
        for a in items[:3]:
            imp = a.get("importance",3)
            dots = "●"*imp + "○"*(5-imp)
            summary = a.get("summary_ko","").replace("\n","<br>")
            html += f"""
          <div style="background:#fff;border:1px solid #E5E7EB;border-radius:8px;padding:10px 12px;margin-bottom:6px;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:4px;">
              <a href="{a.get('url','')}" target="_blank" style="font-size:13px;font-weight:600;color:#1A1A2E;text-decoration:none;flex:1;line-height:1.4;">{a.get('title','')}</a>
              <span style="font-size:11px;color:#F59E0B;white-space:nowrap;">{dots}</span>
            </div>
            <div style="font-size:11px;color:#9CA3AF;margin-bottom:4px;">{a.get('source','')} | 공신력 {a.get('credibility',0):.1f} | {a.get('published','')[:10]}</div>
            {f'<div style="font-size:12px;color:#374151;line-height:1.6;border-top:1px solid #F3F4F6;padding-top:6px;margin-top:6px;">{summary}</div>' if summary else ''}
          </div>"""
        html += "</div>"
    return html


def build_section2(domestic: dict) -> str:
    if not domestic:
        return "<p style='color:#9CA3AF;font-size:13px;'>국내 지표 수집 없음</p>"
    oil = domestic.get("oil_price", {})
    cpi = domestic.get("cpi", {})
    html = f"""
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:12px;">
      <div style="background:#F8F9FA;border-radius:8px;padding:12px;">
        <div style="font-size:11px;color:#9CA3AF;margin-bottom:4px;">휘발유 (전국 평균)</div>
        <div style="font-size:20px;font-weight:600;color:#1A1A2E;">{oil.get('gasoline_national','--')} 원/L</div>
      </div>
      <div style="background:#F8F9FA;border-radius:8px;padding:12px;">
        <div style="font-size:11px;color:#9CA3AF;margin-bottom:4px;">휘발유 (경기도)</div>
        <div style="font-size:20px;font-weight:600;color:#1A1A2E;">{oil.get('gasoline_gyeonggi','--')} 원/L</div>
      </div>
      <div style="background:#F8F9FA;border-radius:8px;padding:12px;">
        <div style="font-size:11px;color:#9CA3AF;margin-bottom:4px;">소비자물가지수</div>
        <div style="font-size:20px;font-weight:600;color:#1A1A2E;">{cpi.get('cpi_latest','--')}</div>
        <div style="font-size:10px;color:#9CA3AF;">{cpi.get('period','')}</div>
      </div>
    </div>"""
    # 경기도 민생 보도자료
    policies = domestic.get("gyeonggi_policy", [])
    if policies:
        html += "<div style='font-size:12px;font-weight:600;color:#374151;margin-bottom:6px;'>경기도 민생 관련 보도자료</div>"
        for p in policies[:3]:
            html += f"""<div style="padding:6px 0;border-bottom:1px solid #F3F4F6;">
              <a href="{p.get('url','')}" target="_blank" style="font-size:12px;color:#185FA5;">{p.get('title','')}</a>
              <span style="font-size:10px;color:#9CA3AF;margin-left:8px;">{p.get('published','')[:10]}</span>
            </div>"""
    return html


def build_section3(minseang: dict) -> str:
    if not minseang:
        return "<p style='color:#9CA3AF;font-size:13px;'>민생 분석 데이터 없음</p>"
    urgency = minseang.get("urgency","모니터링")
    headline = minseang.get("today_headline","")
    urg_bg = RISK_COLOR.get(urgency,"#F1EFE8")
    urg_tc = RISK_TEXT.get(urgency,"#5F5E5A")
    html = f"""
    <div style="background:{urg_bg};border-radius:8px;padding:10px 14px;margin-bottom:12px;display:flex;align-items:center;gap:10px;">
      <span style="font-size:11px;font-weight:600;color:{urg_tc};padding:2px 8px;background:rgba(255,255,255,0.6);border-radius:10px;">{urgency}</span>
      <span style="font-size:13px;font-weight:600;color:{urg_tc};">{headline}</span>
    </div>"""
    impact = minseang.get("impact_analysis", {})
    risk   = minseang.get("risk_level", {})
    for field, text in impact.items():
        field_risk = risk.get(field, "모니터링")
        rb = RISK_COLOR.get(field_risk,"#F1EFE8")
        rt = RISK_TEXT.get(field_risk,"#5F5E5A")
        text_html = text.replace("\n","<br>") if text else ""
        html += f"""
    <div style="background:#fff;border:1px solid #E5E7EB;border-radius:8px;padding:10px 12px;margin-bottom:8px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
        <span style="font-size:12px;font-weight:600;color:#1A1A2E;">{field}</span>
        <span style="font-size:10px;padding:1px 7px;border-radius:10px;background:{rb};color:{rt};">{field_risk}</span>
      </div>
      <div style="font-size:12px;color:#374151;line-height:1.6;">{text_html}</div>
    </div>"""
    return html


def build_section4(paradigm: dict) -> str:
    if not paradigm or not paradigm.get("signals"):
        return "<p style='color:#9CA3AF;font-size:13px;'>오늘 감지된 패러다임 변화 신호 없음</p>"
    html = f"""
    <div style="background:#E8EAF6;border-radius:8px;padding:10px 14px;margin-bottom:12px;">
      <span style="font-size:12px;font-weight:600;color:#283593;">총 {paradigm.get('total_signals',0)}개 신호 감지 | 구조적 변화: {paradigm.get('structural_signals',0)}개</span>
    </div>
    <div style="font-size:12px;color:#374151;background:#fff;border:1px solid #E5E7EB;border-radius:8px;padding:10px 12px;margin-bottom:10px;line-height:1.7;">
      {paradigm.get('summary_ko','').replace(chr(10),'<br>')}
    </div>"""
    for sig in paradigm.get("signals", [])[:5]:
        strength = sig.get("strength", 1)
        bars = "▮"*strength + "▯"*(5-strength)
        src = " · ".join(sig.get("evidence_sources", []))
        desc = sig.get("description","").replace("\n","<br>")
        impl = sig.get("suwon_implication","")
        html += f"""
    <div style="background:#fff;border:1px solid #C5CAE9;border-left:4px solid #3F51B5;border-radius:0 8px 8px 0;padding:10px 12px;margin-bottom:8px;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">
        <span style="font-size:13px;font-weight:600;color:#1A1A2E;">{sig.get('title_ko','')}</span>
        <div style="text-align:right;flex-shrink:0;margin-left:10px;">
          <div style="font-size:11px;color:#3F51B5;">{bars}</div>
          <div style="font-size:10px;color:#9CA3AF;">{sig.get('category','')}</div>
        </div>
      </div>
      <div style="font-size:12px;color:#374151;line-height:1.6;margin-bottom:6px;">{desc}</div>
      {f'<div style="font-size:11px;color:#085041;background:#E1F5EE;padding:4px 8px;border-radius:4px;">수원시 함의: {impl}</div>' if impl else ''}
      <div style="font-size:10px;color:#9CA3AF;margin-top:4px;">소스: {src} | 트렌드: {sig.get('trend','')}</div>
    </div>"""
    return html


def build_section5(minseang: dict) -> str:
    if not minseang:
        return "<p style='color:#9CA3AF;font-size:13px;'>정책 제언 데이터 없음</p>"
    recs = minseang.get("policy_recommendations", {})
    lessons = minseang.get("international_lessons", {})
    html = ""
    labels = {
        "단기_즉시":       ("즉시 대응 (지금 ~ 3개월)", "#FCEBEB", "#A32D2D"),
        "중기_계획":       ("중기 계획 (3 ~ 12개월)",   "#FAEEDA", "#854F0B"),
        "취약계층_우선":   ("취약계층 우선 지원",        "#EAF3DE", "#27500A"),
        "타지자체_벤치마킹":("타 지자체·국외 벤치마킹", "#E6F1FB", "#185FA5"),
    }
    for key, (label, bg, tc) in labels.items():
        items = recs.get(key, [])
        if not items:
            continue
        html += f"""
    <div style="margin-bottom:14px;">
      <div style="font-size:12px;font-weight:600;color:{tc};background:{bg};padding:4px 10px;border-radius:4px;display:inline-block;margin-bottom:6px;">{label}</div>
      <ul style="margin:0;padding-left:18px;">
        {''.join(f'<li style="font-size:12px;color:#374151;margin-bottom:4px;line-height:1.5;">{item}</li>' for item in items)}
      </ul>
    </div>"""
    if lessons:
        html += """<div style="margin-top:12px;padding-top:12px;border-top:1px solid #E5E7EB;">
        <div style="font-size:12px;font-weight:600;color:#374151;margin-bottom:8px;">국내외 대응 사례 참고</div>"""
        for country, lesson in lessons.items():
            html += f"""
        <div style="padding:6px 0;border-bottom:1px solid #F9FAFB;">
          <span style="font-size:11px;font-weight:600;color:#185FA5;margin-right:8px;">{country}</span>
          <span style="font-size:12px;color:#374151;">{lesson}</span>
        </div>"""
        html += "</div>"
    return html


def build_section6(cr: dict) -> str:
    """섹션 6 — 각국 대응 방안 매트릭스 + 이슈 발굴"""
    if not cr or cr.get("error"):
        return "<p style='color:#9CA3AF;font-size:13px;'>각국 대응 데이터 없음</p>"

    html = ""

    # ── 핵심 동향
    key_trends = cr.get("key_trends", [])
    if key_trends:
        html += "<div style='margin-bottom:14px;'>"
        html += "<div style='font-size:12px;font-weight:600;color:#374151;margin-bottom:6px;'>핵심 동향</div>"
        for t in key_trends:
            html += f"<div style='font-size:12px;color:#1A1A2E;background:#F8F9FA;border-left:3px solid #6B7280;padding:6px 10px;border-radius:0 4px 4px 0;margin-bottom:4px;'>{t}</div>"
        html += "</div>"

    # ── 각국 대응 매트릭스
    responses = cr.get("country_responses", [])
    if responses:
        html += """<div style='font-size:12px;font-weight:600;color:#374151;margin-bottom:6px;'>각국·세력 대응 방안 매트릭스</div>
        <div style='overflow-x:auto;margin-bottom:14px;'>
        <table style='width:100%;border-collapse:collapse;font-size:11px;'>
          <thead>
            <tr style='background:#1A1A2E;color:#fff;'>
              <th style='padding:7px 10px;text-align:left;'>국가·세력</th>
              <th style='padding:7px 10px;text-align:left;'>현재 포지션</th>
              <th style='padding:7px 10px;text-align:left;'>구체적 행동</th>
              <th style='padding:7px 10px;text-align:left;'>향후 전망</th>
            </tr>
          </thead>
          <tbody>"""
        for i, cr_item in enumerate(responses):
            bg = "#fff" if i % 2 == 0 else "#F9FAFB"
            actions_html = "".join(
                f"<li style='margin-bottom:2px;'>{a}</li>"
                for a in cr_item.get("actions", [])
            )
            suwon_rel = cr_item.get("suwon_relevance", "")
            html += f"""
            <tr style='background:{bg};border-bottom:1px solid #E5E7EB;'>
              <td style='padding:8px 10px;font-weight:700;color:#1A1A2E;white-space:nowrap;vertical-align:top;'>{cr_item.get('country','')}</td>
              <td style='padding:8px 10px;color:#374151;vertical-align:top;'>{cr_item.get('stance','')}</td>
              <td style='padding:8px 10px;vertical-align:top;'><ul style='margin:0;padding-left:14px;color:#4B5563;'>{actions_html}</ul></td>
              <td style='padding:8px 10px;color:#6B7280;font-style:italic;vertical-align:top;'>
                {cr_item.get('outlook','')}
                {f'<div style="margin-top:4px;font-size:10px;color:#0F6E56;background:#E1F5EE;padding:2px 6px;border-radius:3px;font-style:normal;">수원시: {suwon_rel}</div>' if suwon_rel else ''}
              </td>
            </tr>"""
        html += "</tbody></table></div>"

    # ── 이슈 발굴
    issues = cr.get("emerging_issues", [])
    if issues:
        html += "<div style='font-size:12px;font-weight:600;color:#374151;margin-bottom:6px;'>이슈 발굴 — 주목할 이슈</div>"
        timeline_colors = {
            "단기(1주)":   ("#FCEBEB", "#A32D2D"),
            "중기(1개월)": ("#FAEEDA", "#854F0B"),
            "장기(3개월+)":("#E1F5EE", "#0F6E56"),
        }
        for issue in issues:
            tl = issue.get("timeline", "")
            bg_c, tc_c = timeline_colors.get(tl, ("#F0F7FF", "#1E3A8A"))
            suwon_rel = issue.get("suwon_relevance", "")
            html += f"""
        <div style='background:#F0F7FF;border:1px solid #BFDBFE;border-radius:8px;padding:10px 12px;margin-bottom:8px;'>
          <div style='display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:6px;'>
            <span style='font-size:13px;font-weight:700;color:#1E3A8A;flex:1;'>{issue.get('issue','')}</span>
            {f'<span style="font-size:10px;background:{bg_c};color:{tc_c};padding:2px 7px;border-radius:10px;font-weight:600;white-space:nowrap;">{tl}</span>' if tl else ''}
          </div>
          <div style='font-size:12px;color:#374151;margin-bottom:4px;'><b>왜 중요한가:</b> {issue.get('why_important','')}</div>
          <div style='font-size:12px;color:#374151;margin-bottom:4px;'><b>주목 포인트:</b> {issue.get('watch_for','')}</div>
          {f'<div style="font-size:11px;color:#0F6E56;background:#E1F5EE;padding:3px 8px;border-radius:4px;margin-top:4px;">수원시 연결: {suwon_rel}</div>' if suwon_rel else ''}
        </div>"""

    return html


def build_html(report_date: str, analyzed, domestic, paradigm, minseang, cr=None) -> str:
    total = len(analyzed) if analyzed else 0
    urgency = (minseang or {}).get("urgency", "모니터링")
    urg_bg = RISK_COLOR.get(urgency,"#F1EFE8")
    urg_tc = RISK_TEXT.get(urgency,"#5F5E5A")
    gen_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>수원시 이란전쟁 민생 브리핑 — {report_date}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:'Malgun Gothic','Apple SD Gothic Neo',sans-serif;background:#F8F9FA;color:#1A1A2E;line-height:1.6;}}
.hdr{{background:#1A1A2E;color:#fff;padding:1.5rem 2rem;}}
.hdr h1{{font-size:1.3rem;font-weight:700;margin-bottom:3px;}}
.hdr .meta{{font-size:11px;color:#9CA3AF;}}
.stats{{display:flex;gap:1.5rem;margin-top:10px;flex-wrap:wrap;}}
.stat{{font-size:12px;color:#D1D5DB;}}.stat b{{color:#fff;font-size:16px;}}
.urgency-bar{{background:{urg_bg};padding:8px 2rem;font-size:12px;font-weight:600;color:{urg_tc};}}
.container{{max-width:960px;margin:1.5rem auto;padding:0 1.5rem;}}
.section{{margin-bottom:2rem;background:#fff;border-radius:12px;padding:1.25rem 1.5rem;border:1px solid #E5E7EB;}}
.sec-title{{font-size:14px;font-weight:700;color:#1A1A2E;padding-bottom:10px;border-bottom:2px solid #E5E7EB;margin-bottom:14px;display:flex;align-items:center;gap:8px;}}
.sec-num{{font-size:11px;background:#1A1A2E;color:#fff;padding:2px 8px;border-radius:10px;}}
.footer{{text-align:center;padding:1.5rem;font-size:11px;color:#9CA3AF;}}
</style>
</head>
<body>
<div class="hdr">
  <h1>수원시정연구원 — 이란전쟁 민생 일일 브리핑</h1>
  <div class="meta">기준일: {report_date} | 생성: {gen_at} | 28개 소스 통합</div>
  <div class="stats">
    <div class="stat">수집 기사 <b>{total}</b>건</div>
    <div class="stat">민생 긴급도 <b style="color:{'#F87171' if urgency=='긴급' else '#FCD34D' if urgency=='주의' else '#6EE7B7'};">{urgency}</b></div>
    {'<div class="stat">패러다임 신호 <b>' + str((paradigm or {}).get('total_signals',0)) + '</b>개</div>' if paradigm else ''}
  </div>
</div>
<div class="urgency-bar">
  {(minseang or {}).get('today_headline', '오늘의 민생 헤드라인 없음')}
</div>
<div class="container">

  <div class="section">
    <div class="sec-title"><span class="sec-num">섹션 1</span> 오늘의 전황 요약</div>
    {build_section1(analyzed or [])}
  </div>

  <div class="section">
    <div class="sec-title"><span class="sec-num">섹션 2</span> 오늘의 국내 물가·에너지 지표</div>
    {build_section2(domestic or {})}
  </div>

  <div class="section">
    <div class="sec-title"><span class="sec-num">섹션 3</span> 수원시 민생 영향 분석</div>
    {build_section3(minseang or {})}
  </div>

  <div class="section">
    <div class="sec-title"><span class="sec-num">섹션 4</span> 패러다임 변화 신호</div>
    {build_section4(paradigm or {})}
  </div>

  <div class="section">
    <div class="sec-title"><span class="sec-num">섹션 5</span> 수원시 정책 제언 · 타지자체·국외 사례</div>
    {build_section5(minseang or {})}
  </div>

  <div class="section">
    <div class="sec-title"><span class="sec-num">섹션 6</span> 각국 대응 방안 매트릭스 · 이슈 발굴</div>
    {build_section6(cr or {})}
  </div>

</div>
<div class="footer">
  수원시정연구원 이란전쟁 민생 이슈 발굴 에이전트 v2 | 자동 생성 리포트<br>
  소스: Reuters · AP · BBC · Al Jazeera · 연합뉴스 · CSIS · Guardian · USNI · FT ·
  IEA · IMF · OECD · 세계은행 · UNCTAD · OPEC · KEEI · KIEP · KDI ·
  Chatham House · EU집행위 · 일본METI | 유튜브: AJ · DW · 연합뉴스TV
</div>
</body>
</html>"""


def save_to_db(analyzed: list, report_date: str):
    if not analyzed:
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS articles (
        id TEXT PRIMARY KEY, source TEXT, title TEXT, url TEXT UNIQUE,
        published TEXT, summary TEXT, credibility REAL, lang TEXT,
        category TEXT, summary_ko TEXT, keywords TEXT, importance INTEGER,
        reason TEXT, collected_at TEXT, report_date TEXT)""")
    for a in analyzed:
        try:
            cur.execute("""INSERT INTO articles
              (id,source,title,url,published,summary,credibility,lang,
               category,summary_ko,keywords,importance,reason,collected_at,report_date)
              VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
              ON CONFLICT(id) DO UPDATE SET
              category=excluded.category, summary_ko=excluded.summary_ko,
              importance=excluded.importance""",
              (a.get("id"), a.get("source"), a.get("title"), a.get("url"),
               a.get("published"), a.get("summary"), a.get("credibility"),
               a.get("lang","en"), a.get("category"), a.get("summary_ko"),
               json.dumps(a.get("keywords",[]),ensure_ascii=False),
               a.get("importance",3), a.get("reason"), a.get("collected_at"), report_date))
        except Exception as e:
            logger.debug(f"DB skip: {e}")
    conn.commit(); conn.close()


def run(analyzed_path: Path = None, target_date: str = None) -> Path:
    if target_date is None:
        target_date = date.today().strftime("%Y-%m-%d")
    date_str = target_date.replace("-","")
    if analyzed_path is None:
        analyzed_path = ANALYZED_DIR / f"analyzed_{date_str}.json"

    logger.info(f"=== Reporter 시작: {target_date} ===")

    analyzed = load_json(analyzed_path) or []
    domestic = load_json(DOMESTIC_DIR          / f"domestic_{date_str}.json")
    paradigm = load_json(PARADIGM_DIR          / f"paradigm_{date_str}.json")
    minseang = load_json(POLICY_DIR            / f"minseang_{date_str}.json")
    cr       = load_json(COUNTRY_RESPONSE_DIR  / f"cr_{date_str}.json")

    html = build_html(target_date, analyzed, domestic, paradigm, minseang, cr)

    out_path = REPORTS_DIR / f"report_{date_str}.html"
    out_path.write_text(html, encoding="utf-8")
    logger.info(f"HTML 저장: {out_path}")

    save_to_db(analyzed, target_date)
    logger.info(f"=== Reporter 완료 ===")
    return out_path


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    p = Path(sys.argv[1]) if len(sys.argv)>1 else None
    run(p)
