# TODO

## Google Drive 자동 업로드

### 개요
파이프라인 실행 후 생성된 카드뉴스 이미지를 Google Drive 공유 폴더에 자동 업로드.
업로드 완료 시 알림(Telegram 등) 발송 → 검토 후 수동 인스타 업로드.

### 사전 준비 (Google Cloud Console)

1. **프로젝트 생성**: https://console.cloud.google.com → 새 프로젝트 (무료)
2. **Drive API 활성화**: API 및 서비스 → 라이브러리 → "Google Drive API" 사용
3. **서비스 계정 생성**: 사용자 인증 정보 → 서비스 계정 → JSON 키 다운로드
4. **JSON 키 저장**: 프로젝트 루트에 `credentials.json`으로 저장
5. **Drive 폴더 설정**:
   - Google Drive에 "카드뉴스" 폴더 생성
   - 서비스 계정 이메일(`credentials.json`의 `client_email`)을 편집자로 공유
   - 폴더 ID를 `.env`에 추가

### .env 추가 항목

```
GOOGLE_DRIVE_FOLDER_ID=폴더ID
GOOGLE_CREDENTIALS_PATH=credentials.json
```

### 구현 범위

- `src/uploader/drive.py` — Google Drive 업로드 모듈
  - 날짜별 하위 폴더 생성 (2026-05-30/)
  - post별 하위 폴더 생성 (post_1/, post_2/)
  - slide_1~6.jpg + caption.txt 업로드
- `src/scheduler/pipeline.py` — 렌더링 성공 후 업로드 단계 추가
- 필요 패키지: `google-api-python-client`, `google-auth`

### 파이프라인 흐름 (업로드 추가 후)

```
RSS 크롤링 → 기사 선정 → LLM 콘텐츠 생성 → 카드 렌더링 → Google Drive 업로드 → 알림
```

### 용량 참고

- 슬라이드 1장: 약 200~300KB
- 하루 2세트 (12장): 약 3~5MB
- 한 달: 약 150MB
- Google Drive 무료 15GB 기준 약 8년 사용 가능

### 비용

- Google Cloud 프로젝트 생성 및 Drive API: 무료
- 할당량: 하루 10억 건 쿼리 (우리는 하루 수십 건)

---

## Telegram 알림

### 개요
Google Drive 업로드 완료 시 Telegram 봇으로 알림 발송.
알림에 Drive 폴더 링크 포함 → 바로 검토 가능.

### 사전 준비

1. Telegram에서 @BotFather로 봇 생성 → 토큰 발급
2. 봇과 대화 시작 또는 그룹에 추가
3. Chat ID 확인

### .env 추가 항목

```
TELEGRAM_BOT_TOKEN=토큰
TELEGRAM_CHAT_ID=채팅ID
```

### 구현 범위

- `src/notifier/telegram.py` — 알림 발송 모듈
- 알림 내용: 날짜, 생성된 포스트 수, 성공/실패, Drive 링크

---

## 서버 스케줄링

### 개요
서버에 배포하여 매일 특정 시간에 자동 실행.

### 방법

- **Linux 서버**: crontab으로 `python main.py` 매일 실행
- **클라우드**: AWS Lambda, GCP Cloud Functions, 또는 단순 EC2/GCE에 cron
- 예시: `0 8 * * * cd /path/to/project && .venv/bin/python main.py`

---

## Instagram 자동 업로드 (최종 목표)

### 개요
검토 완료된 카드뉴스를 Instagram에 자동 게시.
현재는 수동 업로드, 추후 자동화.

### 필요 사항

- Meta Business 계정 + Instagram Graph API
- 이미지 퍼블릭 URL 필요 → Cloudinary 또는 Drive 공개 링크
