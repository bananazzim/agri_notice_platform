NOTICE_CATEGORIES = [
    ("support", "Support Program"),
    ("education", "Education"),
    ("contest", "Contest"),
    ("startup", "Startup"),
    ("rd", "R&D"),
    ("job", "Job"),
    ("news", "News"),
    ("other", "Other"),
]

EXCLUDED_NOTICE_CATEGORIES = {"news"}
VISIBLE_NOTICE_CATEGORIES = [
    choice for choice in NOTICE_CATEGORIES if choice[0] not in EXCLUDED_NOTICE_CATEGORIES
]

CRAWLER_METHOD_CHOICES = [
    ("api", "Open API"),
    ("rss", "RSS Feed"),
    ("html", "HTML Crawling"),
    ("playwright", "Playwright"),
]

CRAWLER_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("running", "Running"),
    ("success", "Success"),
    ("failed", "Failed"),
    ("partial", "Partial"),
]

AI_TAGS = [
    "smart_farm",
    "youth_farmer",
    "startup",
    "education",
    "rd",
    "investment",
    "export",
    "competition",
    "agriculture_tech",
    "digital_agriculture",
]

AI_TAGS_KR = {
    "smart_farm": "Smart Farm",
    "youth_farmer": "Youth Farmer",
    "startup": "Startup",
    "education": "Education",
    "rd": "R&D",
    "investment": "Investment",
    "export": "Export",
    "competition": "Competition",
    "agriculture_tech": "Agriculture Tech",
    "digital_agriculture": "Digital Agriculture",
}

RECOMMENDED_FOR = [
    ("student", "Student"),
    ("youth_farmer", "Youth Farmer"),
    ("pre_startup", "Pre-founder"),
    ("startup", "Startup"),
    ("farm_company", "Farm Company"),
    ("agri_corporation", "Agricultural Corporation"),
    ("agri_tech_company", "Agri-tech Company"),
]

IMPORTANCE_SCORE_MIN = 0
IMPORTANCE_SCORE_MAX = 100
IMPORTANCE_SCORE_DEFAULT = 50

SCORE_SOURCE_CHOICES = [
    ("rule", "Rule Based"),
    ("ai", "AI"),
    ("manual", "Manual"),
]

AI_ANALYSIS_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("skipped", "Skipped"),
    ("success", "Success"),
    ("failed", "Failed"),
]

DEADLINE_SOON_DAYS = 7
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

CACHE_TIMEOUT_NOTICE = 3600
CACHE_TIMEOUT_AGENCY = 86400
CACHE_TIMEOUT_STATS = 3600
