# 직접 스크래핑 대상 (RSS/API 미지원 싱크탱크·기관)

SCRAPE_SOURCES = {
    "CSIS_Iran": {
        "url":       "https://www.csis.org/programs/latest-analysis-war-iran",
        "title_sel": "h3.views-field a, h4.card-title a, article h3 a",
        "date_sel":  "time, span.date, .field--type-datetime",
        "base_url":  "https://www.csis.org",
        "credibility": 8.8,
        "schedule":  "daily",
    },
    "Brookings_Iran": {
        "url":       "https://www.brookings.edu/topic/iran/",
        "title_sel": "h4.title a, h3.title a, .search-result-title a",
        "date_sel":  "time, .pub-date",
        "base_url":  "https://www.brookings.edu",
        "credibility": 8.7,
        "schedule":  "daily",
    },
    "CFR_Iran": {
        "url":       "https://www.cfr.org/region/iran",
        "title_sel": "h2.article-header__title a, h3 a",
        "date_sel":  "time, .publication-date",
        "base_url":  "https://www.cfr.org",
        "credibility": 8.6,
        "schedule":  "daily",
    },
    "Britannica_Iran": {
        "url":       "https://www.britannica.com/event/2026-Iran-war",
        "title_sel": "h1.md-crosslink, h2",
        "date_sel":  "time, .metadata-publishdate",
        "base_url":  "https://www.britannica.com",
        "credibility": 9.2,
        "schedule":  "daily",
    },
    "USNI_News": {
        "url":       "https://news.usni.org/category/news",
        "title_sel": "h2.entry-title a, h3.entry-title a",
        "date_sel":  "time.entry-date",
        "base_url":  "https://news.usni.org",
        "credibility": 9.2,
        "schedule":  "daily",
    },
    "IranHR": {
        "url":       "https://iranhr.net/en/articles/",
        "title_sel": "h2 a, h3 a, .article-title a",
        "date_sel":  "time, .date",
        "base_url":  "https://iranhr.net",
        "credibility": 8.0,
        "schedule":  "weekly",  # 주 1회
    },
    "HouseOfCommons": {
        "url":       "https://commonslibrary.parliament.uk/research-briefings/cbp-10521/",
        "title_sel": "h1, h2.briefing-title",
        "date_sel":  "time, .last-updated",
        "base_url":  "https://commonslibrary.parliament.uk",
        "credibility": 9.0,
        "schedule":  "weekly",
    },
}
