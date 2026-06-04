# Cardnews

인스타그램 카드뉴스 자동 생성 파이프라인.

RSS 뉴스 수집 → LLM 요약 → 카드 이미지 렌더링 → Google Drive 업로드 → Telegram 알림

## 기능

- **멀티 계정**: 5개 인스타 계정에 각각 8개 카드뉴스(국내 4 + 해외 4) 자동 생성
- **4개 카테고리**: 경제, 연예, 건강, 스포츠
- **멀티 LLM**: Claude / OpenAI / Gemini 선택 가능 (`LLM_PROVIDER`)
- **자동 스케줄링**: KST 08:00, 13:00 자동 실행
- **Google Drive 업로드**: 생성 후 자동 업로드, 로컬 파일 자동 삭제
- **Telegram 알림**: 파이프라인 완료 시 결과 알림

## 카드뉴스 출력

| 항목 | 스펙 |
|------|------|
| 해상도 | 1080 × 1350 (Instagram 4:5) |
| 형식 | JPEG (quality 92) |
| 구성 | 표지 + 본문 4장 + 출처 = 6장 |
| 언어 | 한국어 (영어 기사도 한국어로 변환) |

## 실행

### 로컬 실행

```bash
# 가상환경 설정
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 의존성 설치
pip install -r requirements.txt
playwright install chromium

# 환경변수 설정
cp .env.example .env
# .env 파일에 API 키 입력

# 1회 실행
python main.py

# 데몬 모드 (APScheduler)
python main.py --daemon
```

### Docker 배포

```bash
# 빌드 & Docker Hub 푸시
make deploy

# 서버에서 실행
# 1. .env 파일 준비
# 2. docker-compose up -d
```

자세한 배포 가이드는 [deploy/README.md](deploy/README.md) 참고.

## 설정

### .env

```env
LLM_PROVIDER=gemini          # openai / claude / gemini
GEMINI_API_KEY=...            # 사용할 LLM의 API 키
SLIDES_PER_POST=6             # 카드 장수
GOOGLE_DRIVE_FOLDER_ID=...    # Drive 업로드 폴더 ID
GOOGLE_CREDENTIALS_PATH=credentials.json
TELEGRAM_BOT_TOKEN=...        # Telegram 알림 봇 토큰
TELEGRAM_CHAT_ID=...          # Telegram 채팅 ID
```

### accounts.yaml

계정과 카테고리를 쉽게 조정:

```yaml
categories:
  - id: economy
    label_ko: "경제"
    accent_color: "#10B981"
  - id: entertainment
    label_ko: "연예"
    accent_color: "#F59E0B"
  # 카테고리 추가/삭제 가능

accounts:
  - handle: "account_1"
    enabled: true
  # 계정 추가/비활성화 가능
```

## 파이프라인

```
RSS 크롤링 (16개 소스)
  ↓
기사 선별 (점수순, 계정별 라운드로빈, 중복 제거)
  ↓
LLM 카드 콘텐츠 생성 (JSON)
  ↓
커버 이미지 (og:image → AI 생성 fallback)
  ↓
Playwright HTML → JPEG 렌더링
  ↓
Google Drive 업로드
  ↓
Telegram 알림
```

## 프로젝트 구조

```
cardnews/
├── config.py                # 설정 (Pydantic + YAML)
├── accounts.yaml            # 계정/카테고리 정의
├── main.py                  # 진입점
├── src/
│   ├── crawler/             # RSS 수집
│   │   ├── rss_sources.py   # 16개 RSS 피드 정의
│   │   ├── fetcher.py       # 크롤러
│   │   └── image_fetcher.py # 커버 이미지
│   ├── selector/ranker.py   # 멀티 계정 선별
│   ├── generator/           # LLM 콘텐츠 생성
│   ├── renderer/            # HTML→JPEG 변환
│   ├── scheduler/pipeline.py # 파이프라인
│   ├── uploader/drive.py    # Google Drive
│   └── notifier/telegram.py # Telegram
├── deploy/                  # Docker 배포 파일
├── data/                    # DB + 출력 (gitignore)
└── tests/                   # pytest
```

## Drive 폴더 구조

```
{날짜}/{계정}/{지역}_{카테고리}/
예: 2026-06-04/account_1/국내_경제/
    ├── slide_1.jpg ~ slide_6.jpg
    └── caption.txt
```
