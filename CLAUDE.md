# Cardnews — AI 뉴스 카드 자동 생성

## 프로젝트 개요
인스타그램 카드뉴스 자동 생성 파이프라인. RSS 뉴스 크롤링 → LLM 요약 → HTML/CSS 카드 렌더링 → Google Drive 업로드.

- **5개 인스타 계정** × **4개 카테고리**(경제/연예/건강/스포츠) × **2개 지역**(국내/해외) = **40개 카드뉴스/회**
- 매일 KST 08:00, 13:00 자동 실행 (UTC 23:00, 04:00)

## 기술 스택
- Python 3.11+, asyncio
- LLM: Claude / OpenAI / Gemini (pluggable, `LLM_PROVIDER` env)
- RSS: feedparser, BeautifulSoup4
- 렌더링: Playwright (Chromium) → 1080×1350 JPEG
- DB: SQLAlchemy + SQLite
- 배포: Docker (Playwright 공식 이미지)

## 핵심 디렉토리 구조
```
config.py              # Pydantic Settings (.env) + YAML 로드
accounts.yaml          # 계정/카테고리 정의 (수정 용이)
main.py                # 진입점 (--daemon으로 APScheduler 모드)
src/
  crawler/             # RSS 크롤링 + 커버이미지
    rss_sources.py     # 16개 RSS 소스 정의
    fetcher.py         # feedparser 크롤링
    image_fetcher.py   # og:image + Gemini Imagen fallback
  selector/ranker.py   # 멀티 계정 라운드로빈 선별
  generator/           # LLM 카드 콘텐츠 생성 (Claude/OpenAI/Gemini)
  renderer/            # HTML 템플릿 → JPEG 변환
  scheduler/pipeline.py # 전체 파이프라인 오케스트레이션
  uploader/drive.py    # Google Drive 업로드
  notifier/telegram.py # Telegram 알림
deploy/                # Docker 배포 파일
```

## 주요 설정 파일
- `.env` — API 키, DB 경로, LLM 프로바이더 선택
- `accounts.yaml` — 카테고리(id/label_ko/accent_color) + 계정(handle/enabled) 정의. 카테고리나 계정 추가/변경은 이 파일만 수정

## 명령어
```bash
python main.py            # 1회 실행 (크롤링→선별→생성→렌더링→업로드)
python main.py --daemon   # APScheduler 데몬 (UTC 04:00, 23:00)
pytest                    # 테스트
```

## 파이프라인 흐름
1. `fetch_all()` — 16개 RSS 소스에서 기사 수집, DB 저장 (중복 제거)
2. `select_for_all_accounts()` — (카테고리×지역) 8슬롯 × 5계정 = 40개 선별, 중복 없음
3. `process_one()` — LLM 생성 → 커버이미지 → Playwright 렌더링 → Drive 업로드 → 로컬 삭제
4. Telegram 알림 발송

## 카드뉴스 선별 기준
점수 = 신선도(48시간 기준) × 소스 가중치(rss_sources.py의 weight) × 제목 품질
- 각 (카테고리, 지역) 풀에서 점수순 정렬 후 계정에 라운드로빈 분배

## Drive 폴더 구조
```
{date}/{account_handle}/{region_label}_{category_label}/
예: 2026-06-04/account_1/국내_경제/slide_1.jpg
```

## 개발 규칙
- 코드 변경 시 기존 파이프라인 흐름(crawl→select→generate→render→upload→notify)을 유지
- accounts.yaml의 카테고리 id는 RSS 소스의 category, ACCENT_COLORS 키, DB의 Article.category와 일치해야 함
- region은 "korean"/"overseas" 두 값만 사용 (language "ko"→"korean", "en"→"overseas")
- Drive 업로드 성공 시 로컬 파일 즉시 삭제 (디스크 절약)
