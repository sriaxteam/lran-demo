# RSS 피드 주소 목록
# 공신력 티어별 분류

# ── 1티어 (최우선 / 매일)
FEEDS_TIER1 = {
    "AP_World":      "https://feeds.apnews.com/rss/apf-worldnews",
    "AP_Top":        "https://feeds.apnews.com/rss/apf-topnews",
    "Reuters_World": "https://feeds.reuters.com/reuters/worldNews",
    "Reuters_Top":   "https://feeds.reuters.com/reuters/topNews",
}

# ── 2티어 (주요 / 매일)
FEEDS_TIER2 = {
    "BBC_MidEast":   "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
    "BBC_World":     "https://feeds.bbci.co.uk/news/world/rss.xml",
    "AlJazeera":     "https://www.aljazeera.com/xml/rss/all.xml",
    "Guardian_Iran": "https://www.theguardian.com/world/iran/rss",
    "Guardian_World":"https://www.theguardian.com/world/rss",
    "NYT_World":     "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "FT_World":      "https://www.ft.com/world?format=rss",
    "Bloomberg":     "https://feeds.bloomberg.com/markets/news.rss",
}

# ── 3티어 (군사·정책 / 매일)
FEEDS_TIER3 = {
    "DefenseOne":    "https://www.defenseone.com/rss/all/",
    "BreakingDef":   "https://breakingdefense.com/feed/",
    "Politico":      "https://rss.politico.com/politics-news.xml",
    "Axios":         "https://api.axios.com/feed/",
    "CSIS":          "https://www.csis.org/rss.xml",
    "CFR":           "https://www.cfr.org/rss.xml",
}

# ── 한국어 피드 (주요)
FEEDS_KO = {
    "Yonhap":        "https://www.yna.co.kr/rss/international.xml",
    "Chosun":        "https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml",
    "Hankyung":      "https://feeds.hankyung.com/article/international.xml",
}

# ── 한국 정책·부처 대응 전용 피드
# 목적: 외교부·산업부·기재부·국토부·식약처·농림부 실제 대응 기사 수집
FEEDS_KO_POLICY = {
    # 연합뉴스 — 정치(부처 발표 빠름) + 경제(에너지·물가 정책)
    "Yonhap_Politics": "https://www.yna.co.kr/rss/politics.xml",
    "Yonhap_Economy":  "https://www.yna.co.kr/rss/economy.xml",
    # 뉴시스 — 정부 부처 발표 전문 보도
    "Newsis":          "https://newsis.com/rss/",
    # 뉴스1 — 부처 정책·긴급 발표 빠른 보도
    "News1":           "https://www.news1.kr/rss/politics.xml",
    # 정책브리핑 — 대한민국 정부 공식 정책 발표 (korea.kr)
    "PolicyBriefing":  "https://www.korea.kr/rss/news.do",
    # 헤럴드경제 — 경제부처·에너지 정책 보도
    "HeraldEco":       "https://biz.heraldkorea.com/rss/rssView.php?cat=all",
}

# ── 지정학·각국 대응 동향 피드 (각국 대응 방안 + 이슈 발굴용)
FEEDS_GEOPOLITICS = {
    "WarOnRocks":       "https://warontherocks.com/feed/",         # 군사·전략 심층분석
    "AtlanticCouncil":  "https://www.atlanticcouncil.org/feed/",   # 대서양 동맹 시각
    "AlMonitor":        "https://www.al-monitor.com/rss",          # 중동 전문 미디어
    "MiddleEastEye":    "https://www.middleeasteye.net/rss",       # 중동 현장
    "ForeignAffairs":   "https://www.foreignaffairs.com/rss.xml",  # 국제관계 심층
    "ForeignPolicy":    "https://foreignpolicy.com/feed/",         # 외교정책 전문
    "AsiaTimes":        "https://asiatimes.com/feed/",             # 아시아 시각
    "SCMP_World":       "https://www.scmp.com/rss/91/feed",        # 중국 시각 (홍콩)
    "EurasiaNet":       "https://eurasianet.org/rss.xml",          # 중앙아·러시아 주변
    "MEI":              "https://www.mei.edu/rss.xml",             # 중동연구소
    "RUSI":             "https://rusi.org/rss.xml",                # 영국 왕립국방안보연구소
}

# ── 전체 통합
ALL_FEEDS = {**FEEDS_TIER1, **FEEDS_TIER2, **FEEDS_TIER3, **FEEDS_KO, **FEEDS_KO_POLICY, **FEEDS_GEOPOLITICS}

# ── 공신력 점수 매핑 (정확성 기준)
CREDIBILITY = {
    "AP_World": 9.5,   "AP_Top": 9.5,
    "Reuters_World": 9.6, "Reuters_Top": 9.6,
    "BBC_MidEast": 9.0,   "BBC_World": 9.0,
    "AlJazeera": 8.0,
    "Guardian_Iran": 8.7, "Guardian_World": 8.7,
    "NYT_World": 8.8,
    "FT_World": 9.1,
    "Bloomberg": 9.0,
    "DefenseOne": 8.0,  "BreakingDef": 8.0,
    "Politico": 8.1,
    "Axios": 7.8,
    "CSIS": 8.8,
    "CFR": 8.6,
    "Yonhap": 8.5,
    "Chosun": 7.8,
    "Hankyung": 8.0,
    # 한국 정책·부처 피드
    "Yonhap_Politics": 8.5,
    "Yonhap_Economy":  8.5,
    "Newsis":          8.0,
    "News1":           7.8,
    "PolicyBriefing":  9.0,   # 정부 공식 발표 — 최고 공신력
    "HeraldEco":       7.8,
    # 지정학·각국 대응 분석
    "WarOnRocks": 8.5,
    "AtlanticCouncil": 8.4,
    "AlMonitor": 8.6,
    "MiddleEastEye": 7.8,
    "ForeignAffairs": 9.0,
    "ForeignPolicy": 8.8,
    "AsiaTimes": 7.5,
    "SCMP_World": 8.0,
    "EurasiaNet": 8.0,
    "MEI": 8.5,
    "RUSI": 8.7,
}
