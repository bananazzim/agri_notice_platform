# Agri Notice Platform

농업, 스마트팜, 창업, R&D, 교육, 경진대회 관련 공고를 기관별 크롤러로 수집하고 Django에서 통합 검색, 필터링, AI 요약을 제공하는 웹 플랫폼입니다.

## 기술 스택

- Python 3.12 이상
- Django 5.x
- PostgreSQL
- Redis
- requests, BeautifulSoup4, feedparser, Playwright
- APScheduler
- OpenAI API
- Bootstrap 5
- Docker, Docker Compose, Nginx, Gunicorn

## 주요 기능

- 기관별 독립 크롤러 구조
- URL 및 `(기관, 제목, 등록일)` 기준 중복 방지
- 제목, 본문, 태그, 기관, 카테고리, 기간, 마감임박 검색
- 최신순, 마감임박순, 중요도순, 조회순 정렬
- OpenAI 기반 3줄 요약, 태그, 중요도 점수, 추천 대상 생성
- APScheduler 기반 매일 09:00 자동 수집
- 관리자에서 기관, 공고, 수집 로그, 수집 상태 관리
- 향후 이메일, 텔레그램, 카카오 알림 확장을 위한 설정 구조

## 프로젝트 구조

```text
agri_notice_platform/
├── ai/
├── apps/
│   ├── notices/
│   └── users/
├── config/
│   └── settings/
├── crawlers/
│   └── agencies/
├── scheduler/
├── services/
├── static/
├── templates/
├── tests/
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── requirements.txt
└── manage.py
```

## 로컬 개발 실행

Windows PowerShell 기준:

```powershell
cd C:\Users\user\Desktop\software2026\agri_notice_platform
.\.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py runserver
```

브라우저에서 `http://127.0.0.1:8000/`로 접속합니다.

## 환경 변수

```powershell
Copy-Item .env.example .env
```

운영 또는 AI 분석을 사용할 때는 최소한 다음 값을 실제 값으로 변경합니다.

```text
SECRET_KEY=...
ALLOWED_HOSTS=your-domain.com,localhost
OPENAI_API_KEY=...
BIZINFO_API_KEY=...
DB_PASSWORD=...
REDIS_PASSWORD=...
```

## 관리 명령

```powershell
# 기관 크롤러 실행
python manage.py run_crawler --agency rda

# 전체 자동 수집 스케줄러 실행
python manage.py start_scheduler

# AI 분석 실행
python manage.py analyze_notices
```

## Docker 실행

Docker Desktop 또는 Docker Engine이 설치된 환경에서 실행합니다.

```bash
cp .env.example .env
docker compose up --build -d
docker compose logs -f web
```

주요 서비스:

- Web: `http://localhost:8000`
- Nginx: `http://localhost`
- PostgreSQL: `${DB_PORT_HOST:-5432}`
- Redis: `${REDIS_PORT_HOST:-6379}`

스케줄러는 별도 `scheduler` 컨테이너에서 `python manage.py start_scheduler`로 실행됩니다.

## 운영 배포 메모

- `SECRET_KEY`, `DB_PASSWORD`, `REDIS_PASSWORD`, `OPENAI_API_KEY`는 반드시 실제 비밀값으로 교체합니다.
- HTTPS 뒤에서 운영할 경우 `SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`를 설정합니다.
- Nginx의 HTTPS 서버 블록은 도메인과 인증서 경로에 맞게 활성화합니다.
- 로그는 컨테이너 볼륨 `logs_volume`에 저장됩니다.

## 테스트

```powershell
pytest
```

다음 단계에서는 테스트 코드를 운영 가능한 수준으로 정비하고 실행 검증합니다.
