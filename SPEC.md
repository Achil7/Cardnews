# AI 뉴스 카드 자동 게시 프로젝트 명세서

> 이 문서 하나만 읽으면 프로젝트 처음부터 끝까지 진행 가능하도록 작성됨.
> Claude Code(VS Code 확장)에 그대로 옮겨서 단계별로 진행할 것.

---

## 0. 문서 사용법

- 각 Phase는 순서대로 진행 (앞 Phase 완료 안 되면 뒤 Phase 불가)
- Phase 0~1은 코드 없이 클릭/설정 작업
- Phase 2부터 코딩 시작
- 각 Phase 끝에 "검증 체크포인트" 있음. 통과해야 다음 Phase로 진행
- `// TODO: 본인 값으로 교체` 표시된 부분은 실제 값 채워 넣을 것

---

## 1. 프로젝트 개요

### 1.1. 목적
AI를 활용해 국내외 뉴스를 자동 수집하고, 인스타그램 카드뉴스 형태로 가공해 운영 계정에 자동 게시하는 시스템 구축.

### 1.2. 목표
- 사람 개입 없이 매일 N개의 카드뉴스를 자동 생성
- 공식 Instagram Graph API를 사용해 계정 정지 위험 없이 자동 업로드
- 콘텐츠 생산 비용(시간) 최소화
- 실패 시에도 카드 이미지는 로컬에 남아 수동 업로드 가능한 안전장치

### 1.3. 최종 산출물
1. 뉴스 크롤링 → 요약 → 카드 이미지 생성 → 인스타 업로드까지 완전 자동화된 파이프라인
2. 매일 정해진 시간에 자동 실행되는 스케줄러
3. 생성된 카드 이미지가 로컬에도 저장됨 (수동 백업/검토 가능)
4. 캡션, 해시태그도 자동 생성되어 함께 게시
5. 텔레그램 봇 알림 (선택사항): 게시 완료/실패 시 본인에게 푸시

### 1.4. 범위
**포함:**
- RSS 기반 뉴스 수집 (네이버, 주요 언론사, 해외 매체)
- LLM(Claude API)으로 요약 및 카드 콘텐츠 생성
- HTML/CSS 템플릿 기반 카드 이미지 렌더링
- Cloudinary를 통한 이미지 호스팅
- Instagram Graph API로 캐러셀 게시
- 일일 자동 실행
- 실패 재시도 및 로깅

**제외 (확장 영역):**
- 릴스/스토리 자동 게시 (1차 완성 이후 추가)
- 다중 인스타 계정 운영
- 웹 관리 대시보드
- 댓글 자동 응답

---

## 2. 시스템 아키텍처

### 2.1. 전체 흐름

```
[1] 뉴스 RSS 크롤링
       ↓
[2] DB 저장 (중복 제거)
       ↓
[3] 게시할 기사 선택 (당일 가장 중요한 N개)
       ↓
[4] Claude API로 카드 콘텐츠 생성 (JSON 구조)
       ↓
[5] HTML 템플릿에 데이터 주입
       ↓
[6] Playwright로 HTML → PNG 변환 (카드 N장)
       ↓
[7] Cloudinary에 이미지 업로드 (공개 URL 획득)
       ↓
[8] Instagram Graph API로 캐러셀 게시
       ↓
[9] 게시 결과 DB 기록 + 텔레그램 알림
```

### 2.2. 컴포넌트 구조

| 컴포넌트 | 역할 | 모듈명 |
|---------|------|--------|
| Crawler | RSS 수집, 본문 추출 | `src/crawler/` |
| Selector | 게시 후보 선정 | `src/selector/` |
| Generator | LLM 호출, 콘텐츠 생성 | `src/generator/` |
| Renderer | HTML→이미지 변환 | `src/renderer/` |
| Uploader | Cloudinary + Instagram 업로드 | `src/uploader/` |
| Scheduler | 전체 파이프라인 오케스트레이션 | `src/scheduler/` |
| Notifier | 텔레그램 알림 | `src/notifier/` |
| DB | 데이터 영속화 | `src/db/` |

---

## 3. 기술 스택

| 영역 | 선택 | 이유 |
|-----|------|-----|
| 언어 | Python 3.11+ | 크롤링/AI/이미지 처리 라이브러리 풍부 |
| DB | SQLite (시작), PostgreSQL (확장 시) | 초기엔 파일 하나로 충분 |
| RSS 파싱 | feedparser | 사실상 표준 |
| HTML 파싱 | BeautifulSoup4 | 본문 추출용 |
| 본문 추출 | newspaper3k | 기사 본문 자동 추출 |
| LLM | Anthropic Claude API (claude-sonnet-4-5) | 한국어 품질 우수, 긴 문맥 |
| 이미지 렌더링 | Playwright | HTML→PNG, 디자인 자유도 |
| 이미지 호스팅 | Cloudinary (무료 tier) | 공개 URL 필요, 무료 25GB |
| 인스타 API | Instagram Graph API (HTTP 직접 호출) | SDK 불필요, requests로 충분 |
| HTTP | requests / httpx | 표준 |
| 스케줄링 | APScheduler 또는 시스템 cron | 환경에 따라 |
| 환경변수 | python-dotenv | `.env` 파일 관리 |
| 로깅 | loguru | 설정 간단 |
| 알림 | python-telegram-bot | 텔레그램 봇 |

---

## 4. 폴더 구조

```
insta-news-bot/
├── .env                          # 환경변수 (gitignore)
├── .env.example                  # 환경변수 템플릿
├── .gitignore
├── README.md
├── requirements.txt
├── pyproject.toml                # (선택) 패키지 메타데이터
├── main.py                       # 진입점
├── config.py                     # 설정 로딩
│
├── src/
│   ├── __init__.py
│   ├── crawler/
│   │   ├── __init__.py
│   │   ├── rss_sources.py        # RSS 소스 목록
│   │   ├── fetcher.py            # RSS 가져오기
│   │   └── extractor.py          # 본문 추출
│   ├── selector/
│   │   ├── __init__.py
│   │   └── ranker.py             # 게시 후보 선정 로직
│   ├── generator/
│   │   ├── __init__.py
│   │   ├── prompt.py             # 프롬프트 템플릿
│   │   └── claude_client.py      # Claude API 호출
│   ├── renderer/
│   │   ├── __init__.py
│   │   ├── render.py             # Playwright 실행
│   │   └── templates/
│   │       ├── card_cover.html   # 표지 슬라이드
│   │       ├── card_body.html    # 본문 슬라이드
│   │       ├── card_outro.html   # 마무리 슬라이드
│   │       └── styles.css        # 공통 스타일
│   ├── uploader/
│   │   ├── __init__.py
│   │   ├── cloudinary_uploader.py
│   │   └── instagram_uploader.py
│   ├── scheduler/
│   │   ├── __init__.py
│   │   └── pipeline.py           # 전체 흐름 오케스트레이션
│   ├── notifier/
│   │   ├── __init__.py
│   │   └── telegram.py
│   └── db/
│       ├── __init__.py
│       ├── models.py             # 테이블 정의
│       └── repository.py         # CRUD
│
├── data/
│   ├── db.sqlite                 # DB 파일
│   └── output/                   # 생성된 카드 이미지
│       └── 2026-05-26/
│           ├── post_1/
│           │   ├── slide_1.png
│           │   ├── slide_2.png
│           │   ├── ...
│           │   └── caption.txt
│           └── post_2/
│
├── logs/
│   └── app.log
│
└── tests/
    ├── test_crawler.py
    ├── test_generator.py
    └── test_renderer.py
```

---

## 5. Phase 0: Meta/Instagram 계정 셋업 (코딩 없음)

> **이 Phase가 가장 짜증나고 가장 자주 막힘. 천천히, 정확히.**
> 본인 계정만 운영하면 앱 심사 불필요. "개발 모드"로 끝까지 충분.

### 5.1. Facebook 개인 계정 준비
1. https://facebook.com 접속
2. 본인 Facebook 계정 로그인 (없으면 새로 가입)
3. **본인 명의/실명 권장.** 가짜 계정으로 만들면 나중에 권한 인증에서 막힐 수 있음.
4. 2단계 인증 켜기 (보안 ▸ 2단계 인증)

### 5.2. Facebook 페이지 생성
1. https://www.facebook.com/pages/create 접속
2. 페이지 이름: 운영할 브랜드명 (예: "오늘의 뉴스 카드")
3. 카테고리: "미디어/뉴스 회사" 또는 "디지털 크리에이터"
4. 설명: 한 줄 설명 입력
5. "페이지 만들기" 클릭
6. **페이지 ID 기록**: 페이지 ▸ 설정 ▸ 페이지 정보 ▸ 페이지 ID
   → 메모장에 `FB_PAGE_ID=...` 형태로 적어둠

### 5.3. Instagram 비즈니스 계정 생성
1. 인스타 앱에서 새 계정 가입 (이메일/전화번호로)
2. 사용자명, 프로필 사진, 소개 작성
3. **프로페셔널 계정 전환:**
   - 프로필 ▸ 메뉴(≡) ▸ 설정 및 개인정보 ▸ 계정 종류 및 도구 ▸ 프로페셔널 계정으로 전환
   - 카테고리: "디지털 크리에이터" 또는 "뉴스 및 미디어 회사"
   - 계정 종류: **"비즈니스"** 선택 (크리에이터 아님)
4. **비공개 계정 해제 확인.** 비즈니스는 공개만 가능.

### 5.4. Instagram ↔ Facebook 페이지 연결
이게 가장 자주 막힘. 두 가지 경로 중 하나로:

**경로 A (인스타 앱에서):**
1. 인스타 프로필 ▸ 프로필 편집 ▸ 페이지
2. "기존 페이지 연결" → 5.2에서 만든 페이지 선택

**경로 B (Facebook 페이지에서):**
1. Facebook 페이지 ▸ 설정 ▸ 연결된 계정 ▸ Instagram
2. "계정 연결" 클릭 → 인스타 로그인

**검증:** Meta Business Suite (https://business.facebook.com) 접속 → 좌측에 인스타 계정과 Facebook 페이지 둘 다 보이면 OK.

### 5.5. Meta 개발자 계정 등록
1. https://developers.facebook.com 접속
2. 우측 상단 "시작하기" 또는 "로그인"
3. 본인 Facebook 계정으로 로그인
4. 전화번호 인증
5. 역할 선택: "개발자"

### 5.6. Meta 앱 생성
1. https://developers.facebook.com/apps 접속
2. "앱 만들기" 클릭
3. **앱 유형: "비즈니스" 선택** (다른 거 고르면 인스타 권한 못 받음)
4. 앱 이름: 아무거나 (예: "InstaNewsBot")
5. 앱 연락처 이메일: 본인 이메일
6. 비즈니스 계정: 없으면 "비즈니스 계정 없이 진행"
7. "앱 만들기" 클릭

### 5.7. Instagram 제품 추가
1. 앱 대시보드 좌측 메뉴 ▸ "제품 추가"
2. **"Instagram"** 찾아서 "설정" 클릭
3. (2024년 이후 통합되어 "Instagram Graph API"가 "Instagram"으로 표시됨)
4. 설정 화면에서 가이드 따라가기

### 5.8. 권한(Permissions) 추가
앱 대시보드 ▸ "앱 검수" ▸ "권한 및 기능" 에서 다음 권한 추가:
- `instagram_basic`
- `instagram_content_publish`
- `pages_show_list`
- `pages_read_engagement`
- `business_management`
- `pages_manage_posts` (선택)

**개발 모드에서는 본인 계정만 사용 가능하므로 심사 불필요.**

### 5.9. 액세스 토큰 발급 (3단계)

#### Step 1: 단기 사용자 토큰 (1시간 유효)
1. https://developers.facebook.com/tools/explorer 접속
2. 우측 상단 "Meta App" 드롭다운 → 본인 앱 선택
3. "User or Page" → "User Token" 선택
4. "Add a Permission" → 5.8의 권한들 모두 추가
5. "Generate Access Token" 클릭 → Facebook 로그인 동의
6. 생성된 토큰 복사 (이게 단기 토큰)

#### Step 2: 장기 사용자 토큰 (60일 유효)
다음 URL에 값 채워서 브라우저 주소창에 입력:
```
https://graph.facebook.com/v21.0/oauth/access_token?
  grant_type=fb_exchange_token
  &client_id={APP_ID}
  &client_secret={APP_SECRET}
  &fb_exchange_token={SHORT_LIVED_TOKEN}
```
- `APP_ID`: 앱 대시보드 ▸ 설정 ▸ 기본 설정 ▸ "앱 ID"
- `APP_SECRET`: 같은 화면 ▸ "앱 시크릿 코드" (보기 클릭)
- `SHORT_LIVED_TOKEN`: Step 1에서 받은 토큰

응답 JSON의 `access_token` 값 = 장기 토큰. 메모장에 저장.

#### Step 3: 영구 페이지 토큰 (만료 없음)
다음 URL:
```
https://graph.facebook.com/v21.0/me/accounts?
  access_token={LONG_LIVED_USER_TOKEN}
```
응답에서 본인 페이지의 `access_token` 값 = **영구 페이지 토큰** (이게 진짜 사용할 토큰).
이 토큰은 만료 없음 (단, 비밀번호 변경 시 재발급 필요).

→ 메모장에 `IG_ACCESS_TOKEN=...`로 저장.

### 5.10. Instagram Business Account ID 확보
다음 URL:
```
https://graph.facebook.com/v21.0/{FB_PAGE_ID}?
  fields=instagram_business_account
  &access_token={PAGE_ACCESS_TOKEN}
```
응답:
```json
{
  "instagram_business_account": { "id": "17841400000000000" },
  "id": "1234567890"
}
```
→ `instagram_business_account.id` 값을 `IG_USER_ID`로 저장.

### 5.11. 수동 테스트 게시 (코드 전에 반드시!)
공개 URL의 이미지 하나로 단일 사진 게시 테스트.

#### Step 1: 미디어 컨테이너 생성
```
POST https://graph.facebook.com/v21.0/{IG_USER_ID}/media
  ?image_url=https://picsum.photos/1080/1080
  &caption=테스트 게시물
  &access_token={IG_ACCESS_TOKEN}
```
응답: `{"id": "1789..."}` ← 컨테이너 ID

#### Step 2: 게시
```
POST https://graph.facebook.com/v21.0/{IG_USER_ID}/media_publish
  ?creation_id={컨테이너 ID}
  &access_token={IG_ACCESS_TOKEN}
```
→ 인스타에 실제로 올라가면 셋업 완료.

### ✅ Phase 0 검증 체크포인트
- [ ] Facebook 페이지 만들었고 ID 확보
- [ ] 인스타 비즈니스 계정 만들었고 페이지와 연결됨
- [ ] Meta 앱 만들었고 Instagram 제품 추가됨
- [ ] 영구 페이지 토큰 발급 완료
- [ ] IG_USER_ID 확보
- [ ] 수동 테스트 게시 성공

**여기 통과 못 하면 절대 코딩 단계로 넘어가지 말 것.**

---

## 6. Phase 1: 개발 환경 셋업

### 6.1. Python 환경
```bash
# Python 3.11+ 설치 확인
python --version

# 프로젝트 폴더 생성
mkdir insta-news-bot && cd insta-news-bot

# 가상환경
python -m venv .venv
# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

# pip 업그레이드
pip install --upgrade pip
```

### 6.2. requirements.txt
```txt
# HTTP
requests==2.32.3
httpx==0.27.2

# RSS / 크롤링
feedparser==6.0.11
beautifulsoup4==4.12.3
lxml==5.3.0
newspaper3k==0.2.8

# LLM
anthropic==0.39.0

# 이미지
playwright==1.48.0
Pillow==11.0.0

# 호스팅
cloudinary==1.41.0

# DB
SQLAlchemy==2.0.36

# 환경/설정
python-dotenv==1.0.1
pydantic==2.9.2
pydantic-settings==2.6.1

# 스케줄
APScheduler==3.10.4

# 로깅
loguru==0.7.2

# 알림 (선택)
python-telegram-bot==21.7

# 유틸
python-dateutil==2.9.0
pytz==2024.2
```

```bash
pip install -r requirements.txt
playwright install chromium
```

### 6.3. .env.example
```env
# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Instagram Graph API
IG_USER_ID=17841400000000000
IG_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxxxxx
FB_PAGE_ID=1234567890

# Cloudinary
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=123456789012345
CLOUDINARY_API_SECRET=your_secret

# Telegram (선택)
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=123456789

# DB
DATABASE_URL=sqlite:///data/db.sqlite

# 운영 설정
POSTS_PER_DAY=2
SLIDES_PER_POST=6
TIMEZONE=Asia/Seoul
LOG_LEVEL=INFO
```

`.env`는 `.env.example`을 복사해서 실제 값 채우기. **절대 git에 커밋 금지.**

### 6.4. .gitignore
```
.venv/
__pycache__/
*.pyc
.env
data/db.sqlite
data/output/
logs/
.pytest_cache/
.DS_Store
```

### 6.5. config.py
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Anthropic
    anthropic_api_key: str

    # Instagram
    ig_user_id: str
    ig_access_token: str
    fb_page_id: str

    # Cloudinary
    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str

    # Telegram (Optional)
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # DB
    database_url: str = "sqlite:///data/db.sqlite"

    # Runtime
    posts_per_day: int = 2
    slides_per_post: int = 6
    timezone: str = "Asia/Seoul"
    log_level: str = "INFO"


settings = Settings()
```

### ✅ Phase 1 검증
- [ ] `python -c "from config import settings; print(settings.ig_user_id)"` 출력 정상
- [ ] `playwright --version` 동작
- [ ] `.env`가 gitignore에 포함됨

---

## 7. Phase 2: DB 스키마

### 7.1. src/db/models.py
```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True, nullable=False, index=True)
    url_hash = Column(String, unique=True, nullable=False, index=True)
    source = Column(String, nullable=False)            # 예: "yonhap", "bbc"
    title = Column(String, nullable=False)
    content = Column(Text)                             # 본문 (선택)
    summary = Column(Text)                             # RSS 요약
    category = Column(String)                          # politics, tech, world, ...
    published_at = Column(DateTime, index=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    score = Column(Float, default=0.0)                 # 랭킹용
    status = Column(String, default="new", index=True)
    # status: new | selected | generated | published | failed | skipped


class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, nullable=False, index=True)
    slides_json = Column(Text)                         # LLM 생성 JSON
    caption = Column(Text)
    hashtags = Column(Text)
    output_dir = Column(String)                        # data/output/2026-05-26/post_1
    cloudinary_urls = Column(Text)                     # JSON array of URLs
    ig_creation_ids = Column(Text)                     # JSON array
    ig_carousel_id = Column(String)
    ig_media_id = Column(String)                       # 최종 게시 ID
    permalink = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime)
    status = Column(String, default="pending", index=True)
    # status: pending | rendered | uploaded | published | failed
    error_log = Column(Text)


class RunLog(Base):
    __tablename__ = "run_logs"
    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    phase = Column(String)                             # crawl, generate, render, upload, publish
    success = Column(Boolean, default=False)
    detail = Column(Text)
```

### 7.2. src/db/repository.py
초기화, 세션 헬퍼, 자주 쓰는 CRUD 함수 작성.
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from config import settings
from .models import Base

engine = create_engine(settings.database_url, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db():
    import os
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(engine)


@contextmanager
def db_session() -> Session:
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
```

### ✅ Phase 2 검증
```bash
python -c "from src.db.repository import init_db; init_db()"
ls data/db.sqlite  # 파일 생성 확인
```

---

## 8. Phase 3: 뉴스 크롤링

### 8.1. src/crawler/rss_sources.py
```python
RSS_SOURCES = [
    # 국내
    {"name": "yonhap", "url": "https://www.yna.co.kr/rss/news.xml", "category": "general"},
    {"name": "hani", "url": "https://www.hani.co.kr/rss/", "category": "general"},
    {"name": "chosun_it", "url": "https://www.chosun.com/arc/outboundfeeds/rss/category/economy/?outputType=xml", "category": "economy"},
    # 해외
    {"name": "bbc_world", "url": "http://feeds.bbci.co.uk/news/world/rss.xml", "category": "world"},
    {"name": "reuters_world", "url": "https://feeds.reuters.com/Reuters/worldNews", "category": "world"},
    {"name": "ap_top", "url": "https://feeds.apnews.com/rss/apf-topnews", "category": "world"},
    # TODO: 본인이 원하는 매체 추가 / 죽은 RSS 제거
]
```
> ⚠️ RSS는 매체 사정으로 죽거나 바뀜. 시작 전에 브라우저로 각 URL 열어서 살아있는지 확인.

### 8.2. src/crawler/fetcher.py
```python
import hashlib
from datetime import datetime
import feedparser
from loguru import logger
from src.db.repository import db_session
from src.db.models import Article
from .rss_sources import RSS_SOURCES


def hash_url(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:32]


def fetch_all() -> int:
    saved = 0
    for src in RSS_SOURCES:
        try:
            feed = feedparser.parse(src["url"])
            logger.info(f"[{src['name']}] {len(feed.entries)} entries")
            for entry in feed.entries:
                url = entry.get("link")
                if not url:
                    continue
                uh = hash_url(url)
                with db_session() as s:
                    exists = s.query(Article).filter_by(url_hash=uh).first()
                    if exists:
                        continue
                    published = None
                    if entry.get("published_parsed"):
                        published = datetime(*entry.published_parsed[:6])
                    a = Article(
                        url=url,
                        url_hash=uh,
                        source=src["name"],
                        title=entry.get("title", "")[:500],
                        summary=entry.get("summary", "")[:2000],
                        category=src["category"],
                        published_at=published or datetime.utcnow(),
                    )
                    s.add(a)
                    saved += 1
        except Exception as e:
            logger.error(f"[{src['name']}] fetch failed: {e}")
    logger.info(f"saved {saved} new articles")
    return saved
```

### 8.3. src/crawler/extractor.py (본문 추출, 선택)
RSS summary가 짧을 때만 본문 가져오기. 사이트 차단 위험 있어서 선택사항.
```python
from newspaper import Article as NPArticle
from loguru import logger


def extract_body(url: str) -> str:
    try:
        a = NPArticle(url, language="ko")
        a.download()
        a.parse()
        return a.text[:5000]
    except Exception as e:
        logger.warning(f"extract failed {url}: {e}")
        return ""
```

### ✅ Phase 3 검증
```bash
python -c "from src.crawler.fetcher import fetch_all; fetch_all()"
# DB에 articles 행이 쌓이는지 확인
```

---

## 9. Phase 4: 게시 후보 선정

### 9.1. src/selector/ranker.py
오늘 게시할 N개 기사를 어떻게 고를지 결정. 간단한 휴리스틱부터:

```python
from datetime import datetime, timedelta
from src.db.repository import db_session
from src.db.models import Article
from config import settings


SOURCE_WEIGHT = {
    "yonhap": 1.2,
    "bbc_world": 1.3,
    "reuters_world": 1.3,
    "ap_top": 1.2,
    "hani": 1.0,
    "chosun_it": 1.0,
}


def score_article(a: Article) -> float:
    # 신선도 (24시간 이내일수록 높음)
    age_hours = (datetime.utcnow() - a.published_at).total_seconds() / 3600 if a.published_at else 999
    freshness = max(0, 24 - age_hours) / 24
    # 매체 가중치
    weight = SOURCE_WEIGHT.get(a.source, 1.0)
    # 제목 길이 (너무 짧거나 길면 감점)
    tl = len(a.title or "")
    title_score = 1.0 if 15 <= tl <= 80 else 0.5
    return freshness * weight * title_score


def select_for_today() -> list[int]:
    with db_session() as s:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        candidates = (
            s.query(Article)
            .filter(Article.status == "new", Article.published_at >= cutoff)
            .all()
        )
        scored = [(a, score_article(a)) for a in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)
        picked = scored[: settings.posts_per_day]
        ids = []
        for a, sc in picked:
            a.status = "selected"
            a.score = sc
            ids.append(a.id)
        return ids
```

> 나중에 더 정교화 가능: LLM으로 "오늘 가장 임팩트 있는 기사" 직접 골라달라고 하기. 카테고리 다양성 보장. 중복 토픽 제거 (제목 임베딩 클러스터링).

### ✅ Phase 4 검증
```bash
python -c "from src.selector.ranker import select_for_today; print(select_for_today())"
```

---

## 10. Phase 5: LLM 콘텐츠 생성

### 10.1. src/generator/prompt.py
```python
SYSTEM_PROMPT = """너는 한국 인스타그램 카드뉴스 콘텐츠 작가야.
주어진 뉴스 기사를 바탕으로 {slides}장짜리 카드뉴스 슬라이드와 캡션, 해시태그를 만든다.

규칙:
- 슬라이드 1번은 "표지" (후킹 제목 + 한 줄 소개)
- 슬라이드 2~{body_end}번은 "본문" (핵심 정보 1슬라이드당 1포인트)
- 마지막 슬라이드는 "출처 + CTA"
- 본문 슬라이드 한 장당 핵심 문장 1개 (40자 이내) + 보조 설명 1~2줄
- 표지 제목은 30자 이내, 임팩트 있게
- 객관적 사실만. 추측/의견 금지
- 출력은 반드시 아래 JSON 스키마. 다른 설명/마크다운 금지.

JSON 스키마:
{{
  "title": "표지 메인 제목",
  "subtitle": "표지 보조 문구",
  "slides": [
    {{"type": "cover", "title": "...", "subtitle": "..."}},
    {{"type": "body", "heading": "...", "body": "..."}},
    ...
    {{"type": "outro", "source": "매체명", "cta": "팔로우 멘트"}}
  ],
  "caption": "인스타 본문 캡션 (2~3문단, 이모지 1~2개)",
  "hashtags": ["#태그1", "#태그2", ...]  // 15~25개
}}
"""


USER_PROMPT = """[기사 정보]
- 매체: {source}
- 카테고리: {category}
- 제목: {title}
- 발행: {published}
- 요약: {summary}
- 본문: {body}

위 기사로 {slides}장짜리 카드뉴스 JSON을 생성해.
"""
```

### 10.2. src/generator/claude_client.py
```python
import json
from anthropic import Anthropic
from loguru import logger
from config import settings
from .prompt import SYSTEM_PROMPT, USER_PROMPT


client = Anthropic(api_key=settings.anthropic_api_key)


def generate_card_content(article: dict) -> dict:
    slides = settings.slides_per_post
    sys_prompt = SYSTEM_PROMPT.format(slides=slides, body_end=slides - 1)
    user_prompt = USER_PROMPT.format(
        source=article["source"],
        category=article.get("category", ""),
        title=article["title"],
        published=str(article.get("published_at", "")),
        summary=(article.get("summary") or "")[:1500],
        body=(article.get("content") or "")[:3000],
        slides=slides,
    )

    resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        system=sys_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = resp.content[0].text.strip()

    # JSON만 추출
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip("` \n")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse failed: {e}\nRaw: {text}")
        raise
    return data
```

### ✅ Phase 5 검증
- 임의 기사 하나로 호출 → JSON 정상 파싱되는지 확인
- 슬라이드 수가 `settings.slides_per_post`와 일치하는지 확인

---

## 11. Phase 6: 카드 이미지 렌더링

### 11.1. 디자인 규격
- 사이즈: **1080 × 1350** (인스타 캐러셀 표준 4:5)
- 포맷: **JPEG** (PNG도 되지만 JPEG가 가장 호환성 좋음)
- 용량: 8MB 이하 (자동으로 그 이하로 나옴)
- 폰트: 웹폰트 (Google Fonts의 "Noto Sans KR" 추천)

### 11.2. src/renderer/templates/styles.css
```css
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap');

* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { width: 1080px; height: 1350px; font-family: 'Noto Sans KR', sans-serif; }

.card {
  width: 1080px;
  height: 1350px;
  padding: 100px 80px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background: #ffffff;
  color: #111111;
}
.cover { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: #fff; }
.body  { background: #f7f7f5; }
.outro { background: #111111; color: #fff; }

.tag { font-size: 28px; font-weight: 700; letter-spacing: 4px; opacity: 0.7; }
.title { font-size: 84px; font-weight: 900; line-height: 1.2; margin-top: 40px; }
.subtitle { font-size: 36px; font-weight: 400; line-height: 1.5; margin-top: 32px; opacity: 0.85; }

.heading { font-size: 64px; font-weight: 900; line-height: 1.25; }
.body-text { font-size: 36px; line-height: 1.6; margin-top: 40px; }

.footer { display: flex; justify-content: space-between; align-items: center; font-size: 24px; opacity: 0.6; }

.source { font-size: 32px; font-weight: 700; }
.cta { font-size: 56px; font-weight: 900; margin-top: 40px; line-height: 1.3; }
```

### 11.3. src/renderer/templates/card_cover.html
```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="styles.css">
</head>
<body>
<div class="card cover">
  <div>
    <div class="tag">{{ category|upper }}</div>
    <div class="title">{{ title }}</div>
    <div class="subtitle">{{ subtitle }}</div>
  </div>
  <div class="footer">
    <span>@{{ handle }}</span>
    <span>{{ date }}</span>
  </div>
</div>
</body>
</html>
```

### 11.4. src/renderer/templates/card_body.html
```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="styles.css">
</head>
<body>
<div class="card body">
  <div>
    <div class="tag">{{ index }} / {{ total }}</div>
    <div class="heading">{{ heading }}</div>
    <div class="body-text">{{ body }}</div>
  </div>
  <div class="footer">
    <span>@{{ handle }}</span>
  </div>
</div>
</body>
</html>
```

### 11.5. src/renderer/templates/card_outro.html
```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="styles.css">
</head>
<body>
<div class="card outro">
  <div>
    <div class="tag">END</div>
    <div class="cta">{{ cta }}</div>
  </div>
  <div class="footer">
    <span class="source">출처: {{ source }}</span>
    <span>@{{ handle }}</span>
  </div>
</div>
</body>
</html>
```

### 11.6. src/renderer/render.py
```python
import os
import asyncio
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright
from loguru import logger


HANDLE = "your_account"  # TODO: 본인 인스타 핸들
TEMPLATE_DIR = Path(__file__).parent / "templates"

env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))


def render_html(slide: dict, index: int, total: int, source: str, category: str) -> str:
    common = {
        "handle": HANDLE,
        "date": datetime.now().strftime("%Y.%m.%d"),
        "index": index,
        "total": total,
        "source": source,
        "category": category,
    }
    if slide["type"] == "cover":
        tpl = env.get_template("card_cover.html")
        return tpl.render(**common, title=slide["title"], subtitle=slide["subtitle"])
    if slide["type"] == "body":
        tpl = env.get_template("card_body.html")
        return tpl.render(**common, heading=slide["heading"], body=slide["body"])
    if slide["type"] == "outro":
        tpl = env.get_template("card_outro.html")
        return tpl.render(**common, cta=slide["cta"], source=slide.get("source", source))
    raise ValueError(slide["type"])


async def html_to_png(html: str, out_path: Path):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1080, "height": 1350}, device_scale_factor=2)
        page = await ctx.new_page()
        # styles.css는 같은 폴더에서 로드되도록 base_url 사용
        await page.set_content(html, wait_until="networkidle")
        await page.goto(f"file://{TEMPLATE_DIR}/blank.html", wait_until="domcontentloaded")
        await page.set_content(html, wait_until="networkidle")
        await page.screenshot(path=str(out_path), type="jpeg", quality=92, full_page=False)
        await browser.close()


async def render_post(post_data: dict, output_dir: Path, source: str, category: str) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    slides = post_data["slides"]
    total = len(slides)
    paths = []
    for i, slide in enumerate(slides, start=1):
        html = render_html(slide, i, total, source, category)
        # 외부 css를 절대경로로 로드하려면 base href 주입
        html = html.replace('href="styles.css"', f'href="file://{TEMPLATE_DIR}/styles.css"')
        out = output_dir / f"slide_{i}.jpg"
        await html_to_png(html, out)
        paths.append(out)
        logger.info(f"rendered {out}")
    # 캡션도 저장
    (output_dir / "caption.txt").write_text(
        post_data.get("caption", "") + "\n\n" + " ".join(post_data.get("hashtags", [])),
        encoding="utf-8",
    )
    return paths
```

> **검증 팁:** 코드 실행 전에 HTML 템플릿을 그냥 브라우저로 열어서 디자인 먼저 확인. 디자인 만족스러우면 그제서야 Playwright로 캡처.

### ✅ Phase 6 검증
- `data/output/2026-05-26/post_1/slide_1.jpg ~ slide_N.jpg` 생성됨
- 이미지 직접 열어서 디자인/글자 깨짐 확인
- 사이즈 1080×1350 확인

---

## 12. Phase 7: Cloudinary 업로드

### 12.1. Cloudinary 셋업
1. https://cloudinary.com 가입 (무료)
2. Dashboard에서 `Cloud Name`, `API Key`, `API Secret` 복사 → `.env`에 입력

### 12.2. src/uploader/cloudinary_uploader.py
```python
import cloudinary
import cloudinary.uploader
from pathlib import Path
from loguru import logger
from config import settings


cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
    secure=True,
)


def upload_images(paths: list[Path], folder: str) -> list[str]:
    urls = []
    for p in paths:
        res = cloudinary.uploader.upload(
            str(p),
            folder=f"insta-news/{folder}",
            resource_type="image",
            overwrite=True,
        )
        urls.append(res["secure_url"])
        logger.info(f"cloudinary: {res['secure_url']}")
    return urls
```

### ✅ Phase 7 검증
- 업로드된 URL을 브라우저로 열어 이미지 보이는지 확인
- HTTPS URL 인지 확인 (인스타 API는 HTTPS만 받음)

---

## 13. Phase 8: Instagram 캐러셀 업로드

### 13.1. src/uploader/instagram_uploader.py
```python
import time
import json
import requests
from loguru import logger
from config import settings


GRAPH = "https://graph.facebook.com/v21.0"


def _create_item_container(image_url: str) -> str:
    """캐러셀 자식 미디어 컨테이너 생성"""
    r = requests.post(
        f"{GRAPH}/{settings.ig_user_id}/media",
        data={
            "image_url": image_url,
            "is_carousel_item": "true",
            "access_token": settings.ig_access_token,
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["id"]


def _create_carousel_container(children_ids: list[str], caption: str) -> str:
    r = requests.post(
        f"{GRAPH}/{settings.ig_user_id}/media",
        data={
            "media_type": "CAROUSEL",
            "children": ",".join(children_ids),
            "caption": caption,
            "access_token": settings.ig_access_token,
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["id"]


def _wait_until_finished(creation_id: str, timeout: int = 120) -> None:
    """미디어 처리 완료까지 폴링"""
    start = time.time()
    while time.time() - start < timeout:
        r = requests.get(
            f"{GRAPH}/{creation_id}",
            params={"fields": "status_code", "access_token": settings.ig_access_token},
            timeout=30,
        )
        r.raise_for_status()
        status = r.json().get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"media processing error: {r.json()}")
        time.sleep(3)
    raise TimeoutError("media not finished in time")


def _publish(creation_id: str) -> dict:
    r = requests.post(
        f"{GRAPH}/{settings.ig_user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": settings.ig_access_token},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def _get_permalink(media_id: str) -> str:
    r = requests.get(
        f"{GRAPH}/{media_id}",
        params={"fields": "permalink", "access_token": settings.ig_access_token},
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("permalink", "")


def publish_carousel(image_urls: list[str], caption: str) -> dict:
    if not (2 <= len(image_urls) <= 10):
        raise ValueError("carousel must have 2~10 images")

    logger.info(f"creating {len(image_urls)} child containers")
    children = [_create_item_container(u) for u in image_urls]
    for cid in children:
        _wait_until_finished(cid)

    logger.info("creating carousel container")
    carousel_id = _create_carousel_container(children, caption)
    _wait_until_finished(carousel_id)

    logger.info("publishing")
    pub = _publish(carousel_id)
    media_id = pub["id"]
    permalink = _get_permalink(media_id)
    return {
        "media_id": media_id,
        "carousel_id": carousel_id,
        "children": children,
        "permalink": permalink,
    }
```

### 13.2. 캡션 + 해시태그 합치기
```python
def build_caption(caption: str, hashtags: list[str]) -> str:
    # 인스타 캡션 최대 2200자. 해시태그 최대 30개.
    tags = " ".join(hashtags[:30])
    full = f"{caption}\n\n.\n.\n.\n{tags}"
    return full[:2200]
```

### ✅ Phase 8 검증
- 실제 운영 계정에 캐러셀 한 번 올라감
- DB의 `posts` 테이블에 `ig_media_id`, `permalink` 채워짐

---

## 14. Phase 9: 전체 파이프라인 오케스트레이션

### 14.1. src/scheduler/pipeline.py
```python
import asyncio
import json
from datetime import datetime
from pathlib import Path
from loguru import logger
from src.db.repository import db_session, init_db
from src.db.models import Article, Post
from src.crawler.fetcher import fetch_all
from src.selector.ranker import select_for_today
from src.generator.claude_client import generate_card_content
from src.renderer.render import render_post
from src.uploader.cloudinary_uploader import upload_images
from src.uploader.instagram_uploader import publish_carousel, build_caption
from src.notifier.telegram import notify  # 없으면 더미


async def process_one(article_id: int):
    with db_session() as s:
        a = s.get(Article, article_id)
        article_dict = {
            "id": a.id, "source": a.source, "category": a.category,
            "title": a.title, "summary": a.summary, "content": a.content,
            "published_at": a.published_at,
        }
        post = Post(article_id=a.id, status="pending")
        s.add(post)
        s.flush()
        post_id = post.id

    # 1. LLM 생성
    try:
        data = generate_card_content(article_dict)
    except Exception as e:
        logger.exception("generate failed")
        with db_session() as s:
            s.get(Post, post_id).status = "failed"
            s.get(Post, post_id).error_log = f"generate: {e}"
        return

    # 2. 렌더링
    today = datetime.now().strftime("%Y-%m-%d")
    out_dir = Path("data/output") / today / f"post_{post_id}"
    try:
        paths = await render_post(data, out_dir, source=a.source, category=a.category or "")
    except Exception as e:
        logger.exception("render failed")
        with db_session() as s:
            s.get(Post, post_id).status = "failed"
            s.get(Post, post_id).error_log = f"render: {e}"
        return

    with db_session() as s:
        p = s.get(Post, post_id)
        p.slides_json = json.dumps(data, ensure_ascii=False)
        p.caption = data.get("caption", "")
        p.hashtags = json.dumps(data.get("hashtags", []), ensure_ascii=False)
        p.output_dir = str(out_dir)
        p.status = "rendered"

    # 3. Cloudinary 업로드
    try:
        urls = upload_images(paths, folder=f"{today}/post_{post_id}")
    except Exception as e:
        logger.exception("cloudinary failed")
        with db_session() as s:
            s.get(Post, post_id).status = "failed"
            s.get(Post, post_id).error_log = f"cloudinary: {e}"
        return

    with db_session() as s:
        p = s.get(Post, post_id)
        p.cloudinary_urls = json.dumps(urls)
        p.status = "uploaded"

    # 4. 인스타 게시
    caption = build_caption(data.get("caption", ""), data.get("hashtags", []))
    try:
        result = publish_carousel(urls, caption)
    except Exception as e:
        logger.exception("instagram publish failed")
        with db_session() as s:
            s.get(Post, post_id).status = "failed"
            s.get(Post, post_id).error_log = f"instagram: {e}"
        notify(f"❌ 게시 실패 (post {post_id}): {e}")
        return

    with db_session() as s:
        p = s.get(Post, post_id)
        p.ig_media_id = result["media_id"]
        p.ig_carousel_id = result["carousel_id"]
        p.ig_creation_ids = json.dumps(result["children"])
        p.permalink = result["permalink"]
        p.published_at = datetime.utcnow()
        p.status = "published"
        a2 = s.get(Article, a.id)
        a2.status = "published"

    notify(f"✅ 게시 완료\n{result['permalink']}")


async def run_pipeline():
    init_db()
    logger.info("=== Pipeline start ===")
    fetched = fetch_all()
    ids = select_for_today()
    logger.info(f"fetched={fetched} selected={len(ids)}")
    for aid in ids:
        await process_one(aid)
    logger.info("=== Pipeline done ===")


if __name__ == "__main__":
    asyncio.run(run_pipeline())
```

### 14.2. main.py
```python
import asyncio
from src.scheduler.pipeline import run_pipeline

if __name__ == "__main__":
    asyncio.run(run_pipeline())
```

### ✅ Phase 9 검증
```bash
python main.py
```
끝까지 돌아가서 인스타에 카드뉴스 캐러셀이 올라가면 성공.

---

## 15. Phase 10: 스케줄링

### 15.1. 옵션 A — 시스템 cron (Linux/Mac)
```bash
crontab -e
# 매일 오전 9시 실행
0 9 * * * cd /path/to/insta-news-bot && /path/to/.venv/bin/python main.py >> logs/cron.log 2>&1
```

### 15.2. 옵션 B — Windows 작업 스케줄러
1. 작업 스케줄러 → 작업 만들기
2. 트리거: 매일 09:00
3. 동작: 프로그램 시작
   - 프로그램: `C:\path\to\.venv\Scripts\python.exe`
   - 인수: `main.py`
   - 시작 위치: `C:\path\to\insta-news-bot`

### 15.3. 옵션 C — APScheduler로 상시 실행
```python
# scheduler_daemon.py
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.scheduler.pipeline import run_pipeline
from config import settings

async def main():
    sch = AsyncIOScheduler(timezone=settings.timezone)
    sch.add_job(run_pipeline, "cron", hour=9, minute=0)
    sch.start()
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
```

### 15.4. 옵션 D — GitHub Actions (서버 없이)
`.github/workflows/run.yml`:
```yaml
name: Daily Run
on:
  schedule:
    - cron: "0 0 * * *"  # UTC 00:00 = KST 09:00
  workflow_dispatch:
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r requirements.txt
      - run: playwright install chromium
      - run: python main.py
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          IG_USER_ID: ${{ secrets.IG_USER_ID }}
          IG_ACCESS_TOKEN: ${{ secrets.IG_ACCESS_TOKEN }}
          FB_PAGE_ID: ${{ secrets.FB_PAGE_ID }}
          CLOUDINARY_CLOUD_NAME: ${{ secrets.CLOUDINARY_CLOUD_NAME }}
          CLOUDINARY_API_KEY: ${{ secrets.CLOUDINARY_API_KEY }}
          CLOUDINARY_API_SECRET: ${{ secrets.CLOUDINARY_API_SECRET }}
```
> 단점: GitHub Actions는 DB가 매번 초기화됨. SQLite를 commit하거나 외부 DB(예: Supabase) 써야 함.

---

## 16. Phase 11: 텔레그램 알림 (선택)

### 16.1. 봇 생성
1. 텔레그램에서 `@BotFather` 검색
2. `/newbot` → 이름 입력 → 토큰 받음
3. 본인이 만든 봇에게 아무 메시지 한 번 보내기
4. https://api.telegram.org/bot{TOKEN}/getUpdates 에서 `chat.id` 확인 → `.env`에 입력

### 16.2. src/notifier/telegram.py
```python
import requests
from loguru import logger
from config import settings


def notify(text: str) -> None:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
            data={"chat_id": settings.telegram_chat_id, "text": text},
            timeout=10,
        )
    except Exception as e:
        logger.warning(f"telegram notify failed: {e}")
```

---

## 17. Phase 12: 로깅 설정

`main.py` 상단 또는 `config.py`에:
```python
from loguru import logger
import sys, os

os.makedirs("logs", exist_ok=True)
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("logs/app.log", rotation="10 MB", retention="30 days", level="DEBUG", encoding="utf-8")
```

---

## 18. 운영 / 유지보수

### 18.1. 토큰 관리
- 영구 페이지 토큰은 비밀번호 변경/2FA 변경 시 만료 → 알림 받으면 5.9 다시 실행
- 토큰 유효성 체크 스크립트 작성 권장:
```python
# tools/check_token.py
import requests
from config import settings
r = requests.get(
    f"https://graph.facebook.com/v21.0/{settings.ig_user_id}",
    params={"fields": "username", "access_token": settings.ig_access_token},
)
print(r.status_code, r.json())
```

### 18.2. DB 백업
- SQLite면 그냥 파일 복사
- 매주 1회 `data/db.sqlite`를 클라우드 드라이브에 백업

### 18.3. Cloudinary 무료 한도 관리
- 무료 25GB. 카드 이미지 1장 ~500KB 가정 시 약 5만 장 보관 가능
- 30일 지난 폴더 자동 삭제 스크립트 만들면 좋음

### 18.4. 비용 추정 (월간)
- Claude API: 기사 2개/일 × 30일 × ~1,500 토큰 = 매우 저렴 (월 $1~3)
- Cloudinary: 무료 tier로 충분
- 인스타 API: 무료
- 호스팅: cron이면 본인 PC, GitHub Actions는 무료 (월 2000분 내)
- **총: 월 $1~5 수준**

### 18.5. 실패 복구
- 모든 실패는 DB `Post.status="failed"` + `error_log`에 기록
- 카드 이미지는 `data/output/`에 항상 남아있음 → 인스타 업로드 실패해도 수동 백업 가능
- 텔레그램 알림으로 즉시 인지

---

## 19. 보안 / 콘텐츠 정책 주의

### 19.1. 보안
- `.env` 절대 git에 커밋 금지
- 영구 페이지 토큰 노출 시 즉시 https://developers.facebook.com에서 앱 시크릿 재발급
- 운영 인스타 계정에 2FA 켜기 (API 사용과 무관하게 OK)

### 19.2. 콘텐츠 정책
- 인스타 정책 위반 시 API 사용해도 제재됨
- 저작권: 기사 원문 그대로 복붙 ❌ → 반드시 요약/재구성
- 출처 명시 의무화 (마지막 슬라이드에)
- 자극적/혐오/허위 정보 필터링 (LLM 프롬프트에 명시)
- 동일 콘텐츠 도배 금지

### 19.3. 인스타 API 제한
- 일일 게시: 50개 미만 권장
- 캐러셀: 2~10장
- 캡션: 2,200자, 해시태그 30개
- 미디어 처리: 비동기 (FINISHED 대기 필수, 코드에 반영됨)

---

## 20. 향후 확장 로드맵

| 단계 | 기능 |
|-----|------|
| v1 | 본 명세 (캐러셀 자동 게시) |
| v1.1 | 스토리 자동 게시 (`media_type=STORIES`) |
| v1.2 | 릴스 자동 게시 (LLM으로 짧은 영상 스크립트 → 영상 생성) |
| v2 | 카테고리별 다중 계정 운영 |
| v2.1 | 댓글 모니터링 (조회만, 자동 응답 X) |
| v2.2 | 인사이트 수집 (조회수, 좋아요 → DB → 최적 게시 시간 학습) |
| v3 | 웹 대시보드 (Next.js / Streamlit) |

---

## 21. 부록 A: 자주 막히는 트러블슈팅

| 증상 | 원인 / 해결 |
|------|------------|
| `instagram_business_account` 응답 없음 | 페이지-인스타 연결 미완료. 5.4 다시. |
| `(#10) Application does not have permission` | 5.8 권한 추가 누락. `instagram_content_publish` 확인. |
| `(#190) Error validating access token` | 토큰 만료/무효. 5.9 다시. |
| `Media type is not supported` | 이미지가 JPEG/PNG가 아니거나 너무 큼. 1080×1350 JPEG로 변환. |
| `image_url` 다운로드 실패 | Cloudinary URL이 HTTP거나, 권한 막힘. HTTPS + 공개 URL 확인. |
| 캐러셀 publish 시 `Media not ready` | `_wait_until_finished` 대기 누락. |
| Playwright `Executable doesn't exist` | `playwright install chromium` 실행 안 함. |
| 한글 폰트 깨짐 | Google Fonts import 누락 또는 `networkidle` 미대기. 렌더 시 `wait_until="networkidle"` 확인. |
| `feedparser` 빈 결과 | RSS URL이 죽음. 브라우저로 직접 열어 확인. |
| GitHub Actions에서 DB 초기화됨 | SQLite 대신 Supabase/PostgreSQL 같은 외부 DB로 전환. |

---

## 22. 부록 B: 작업 진행 체크리스트

처음 셋업 시 위에서 아래로 순서대로:

- [ ] Phase 0: Facebook 페이지 생성
- [ ] Phase 0: 인스타 비즈니스 계정 + 페이지 연결
- [ ] Phase 0: Meta 앱 생성 + 권한 추가
- [ ] Phase 0: 영구 페이지 토큰 발급
- [ ] Phase 0: IG_USER_ID 확보
- [ ] Phase 0: Graph API Explorer로 수동 테스트 게시 성공
- [ ] Phase 1: Python 환경 + requirements.txt 설치
- [ ] Phase 1: `.env` 채우기
- [ ] Phase 2: DB 초기화
- [ ] Phase 3: 크롤링 테스트 (DB에 데이터 쌓이는지)
- [ ] Phase 4: 선정 로직 테스트
- [ ] Phase 5: LLM 호출 + JSON 파싱 테스트
- [ ] Phase 6: 카드 1장 렌더링 테스트 (디자인 확인)
- [ ] Phase 6: 전체 슬라이드 렌더링 성공
- [ ] Phase 7: Cloudinary 업로드 성공
- [ ] Phase 8: 인스타 캐러셀 자동 게시 성공
- [ ] Phase 9: `main.py` 전체 파이프라인 1회 성공
- [ ] Phase 10: 스케줄러 셋업
- [ ] Phase 11: 텔레그램 알림 (선택)
- [ ] Phase 12: 로깅 동작 확인
- [ ] 토큰 체크 스크립트 실행 잘 됨
- [ ] 30일 운영 후 발생 이슈 회고

---

## 23. 부록 C: Claude Code에서 작업할 때 추천 흐름

1. 이 문서를 프로젝트 루트에 `SPEC.md`로 저장
2. Claude Code에 다음과 같이 지시:
   > `SPEC.md` 보고 Phase 1부터 순서대로 진행해줘. 각 Phase 끝나면 검증 체크포인트 통과 여부 확인하고 다음 Phase로 가.
3. Phase 0(계정 셋업)은 본인이 직접 수행 (자동화 불가)
4. Phase 1부터 Claude Code가 폴더/파일 생성, 코드 작성, 테스트까지 가능
5. 각 Phase 완료 시 git commit 권장:
   ```
   git commit -m "feat: phase 3 - news crawler implemented"
   ```

---

문서 끝.
