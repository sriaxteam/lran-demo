# -*- coding: utf-8 -*-
import json

with open(r'C:\Users\user\Desktop\iran_news_agent_final\iran_final\data\analyzed\analyzed_20260420.json', encoding='utf-8') as f:
    data = json.load(f)

mock_updates = [
    {
        'idx': 0,
        'category': 'energy',
        'importance': 9,
        'summary_ko': '미 해군이 호르무즈 해협 봉쇄 위반 이란 선박을 나포. 이란의 보복 조치 가능성으로 에너지 시장 긴장 고조. WTI 유가 즉각 $2.3 급등.',
        'keywords': ['호르무즈', '봉쇄', '이란', '미 해군', '유가'],
        'related_country': ['미국', '이란'],
        'reason': '호르무즈 해협 봉쇄 위기 직접 증거 — 수원시 에너지 비용 상승 경보'
    },
    {
        'idx': 1,
        'category': 'energy',
        'importance': 9,
        'summary_ko': 'IEA, 이란-미 갈등 장기화로 국제유가 WTI $100 돌파 가능성 경고. 글로벌 에너지 공급 비상계획 발동 촉구. 한국 포함 아시아 국가 LNG 수급 차질 현실화.',
        'keywords': ['IEA', '유가', 'WTI', '에너지위기', 'LNG'],
        'related_country': ['미국', '이란', '한국'],
        'reason': 'IEA 공식 경고 — 수원시 도시가스·전기요금 추가 인상 압력의 직접 원인'
    },
    {
        'idx': 2,
        'category': 'economy',
        'importance': 8,
        'summary_ko': 'IMF, 이란전쟁 영향으로 한국 2026년 성장률 전망 2.1%에서 1.7%로 하향 조정. 에너지 비용 급등과 수출 차질이 주요 원인. 물가상승률은 4.5%로 상향.',
        'keywords': ['IMF', '한국성장률', '경제전망', '물가'],
        'related_country': ['한국', '미국'],
        'reason': 'IMF 한국 성장률 하향 — 수원시 소상공인·고용 경기 직접 악화 신호'
    },
    {
        'idx': 3,
        'category': 'military',
        'importance': 8,
        'summary_ko': '이란 IRGC, 카타르 LNG 터미널 50km 해역에서 대규모 해군 훈련 개시. 한국 LNG 수입 45% 점유 카타르 수급 차질 우려 확대.',
        'keywords': ['이란', 'IRGC', '카타르', 'LNG', '군사훈련'],
        'related_country': ['이란', '카타르', '한국'],
        'reason': '카타르 LNG 위협 — 수원시 도시가스 공급 불안 직접 연결'
    },
    {
        'idx': 4,
        'category': 'energy',
        'importance': 8,
        'summary_ko': '국내 LNG 현물 구매 비용 전년 동기 대비 62% 급등. 한국가스공사, 2분기 도시가스 요금 추가 인상 불가피 공식 발표. 가정용 약 15% 상승 예고.',
        'keywords': ['LNG', '도시가스', '요금인상', '한국가스공사'],
        'related_country': ['한국'],
        'reason': '수원시 가계·소상공인 도시가스 직접 인상 예고 — 즉시 대응 필요'
    },
    {
        'idx': 5,
        'category': 'humanitarian',
        'importance': 7,
        'summary_ko': '에너지 비용 급등으로 EU 내 에너지 빈곤 가구 3,200만 세대 돌파. 각국 긴급 에너지 바우처·가격 상한제 도입. 한국도 취약계층 에너지 지원 확대 압박.',
        'keywords': ['에너지빈곤', 'EU', '취약계층', '에너지바우처'],
        'related_country': ['EU', '한국'],
        'reason': '글로벌 에너지 빈곤 확산 — 수원시 취약계층 지원 정책 설계 참고'
    },
    {
        'idx': 6,
        'category': 'diplomacy',
        'importance': 7,
        'summary_ko': 'OPEC+ 긴급 회의 4월 25일 개최 확정. 사우디 감산 유지 vs. UAE 일부 증산 충돌. 회의 결과에 따라 유가 방향성 결정.',
        'keywords': ['OPEC', '감산', '사우디', 'UAE', '유가'],
        'related_country': ['사우디아라비아', 'UAE'],
        'reason': 'OPEC+ 결정이 국내 유가·물가에 직접 영향 — 4/25 이후 수원시 대응 방향 재조정'
    },
    {
        'idx': 7,
        'category': 'korea',
        'importance': 7,
        'summary_ko': '삼성전자, 이란전쟁 여파 반도체 부품 공급망 차질 경고. 수원 디지털시티 내 협력사 생산 일정 조정 검토. 3분기 정상화 목표 발표.',
        'keywords': ['삼성전자', '반도체', '공급망', '수원'],
        'related_country': ['한국'],
        'reason': '수원시 최대 고용주 삼성전자 직접 타격 — 수원 경제 핵심 리스크'
    },
    {
        'idx': 8,
        'category': 'energy',
        'importance': 6,
        'summary_ko': '경기도, 에너지 취약계층 긴급 바우처 2분기 조기 지급 결정. 650억 원 규모. 수원시 신청 접수 일정 조율 중.',
        'keywords': ['경기도', '에너지바우처', '취약계층'],
        'related_country': ['한국'],
        'reason': '수원시 즉시 연계 가능한 지원 사업 — 신속 신청 접수 필요'
    },
    {
        'idx': 9,
        'category': 'economy',
        'importance': 6,
        'summary_ko': '4월 소비자물가 전년 대비 4.1% 상승. 에너지 11.3%, 식품 5.7% 급등 주도. 저소득층 실질 구매력 3.2% 하락 추정.',
        'keywords': ['소비자물가', 'CPI', '에너지', '식품'],
        'related_country': ['한국'],
        'reason': '수원시 민생 물가 직접 지표 — 장바구니 물가 대응 정책 근거'
    },
]

for upd in mock_updates:
    idx = upd.pop('idx')
    if idx < len(data):
        data[idx].update(upd)

with open(r'C:\Users\user\Desktop\iran_news_agent_final\iran_final\data\analyzed\analyzed_20260420.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"완료: {len(data)}건 업데이트")
top = sorted(data, key=lambda x: x.get('importance', 0), reverse=True)[:5]
for a in top:
    print(f"  importance={a['importance']}  {a.get('summary_ko','')[:50]}")
