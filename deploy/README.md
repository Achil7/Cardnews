# Cardnews 서버 배포 가이드

## 빌드 & 푸시 (로컬에서)

```bash
# 빌드 + 태그 + Docker Hub 푸시 (한번에)
make deploy

# 또는 개별 실행
make build    # Docker 이미지 빌드
make tag      # Docker Hub용 태그
make push     # Docker Hub 푸시
```

## 서버 배포 (EWC 서버에서)

### 1. 배포 디렉토리 준비

```bash
mkdir -p ~/cardnews && cd ~/cardnews
```

### 2. 필요 파일 복사

서버의 `~/cardnews/` 디렉토리에 다음 파일을 준비:

```
~/cardnews/
├── docker-compose.yml    # 이 디렉토리의 파일 복사
├── .env                  # .env.example 복사 후 실제 값 입력
├── credentials.json      # Google Cloud 서비스 인증 JSON
├── token.json            # Google Drive OAuth 토큰 (로컬에서 최초 인증 후 복사)
├── accounts.yaml         # 계정/카테고리 설정
└── deploy.sh             # 배포 스크립트
```

### 3. .env 설정

```bash
cp .env.example .env
vi .env
```

필수 항목:
- `LLM_PROVIDER` + 해당 API 키
- `GOOGLE_DRIVE_FOLDER_ID` — Drive 업로드 대상 폴더 ID
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` — 알림용

### 4. Google Drive 인증

**최초 1회만 로컬에서 실행** (브라우저 인증 필요):

```bash
# 로컬 PC에서
python main.py
# 브라우저가 열리면 Google 계정 인증
# token.json 파일이 생성됨
```

생성된 `token.json`을 서버로 복사:
```bash
scp token.json user@server:~/cardnews/
scp credentials.json user@server:~/cardnews/
```

### 5. 배포 실행

```bash
chmod +x deploy.sh
./deploy.sh
```

### 6. 확인

```bash
# 컨테이너 상태
docker ps

# 로그 확인
docker logs -f cardnews-app

# 수동 실행 테스트
docker exec cardnews-app python main.py
```

## 스케줄

컨테이너 내부 cron으로 자동 실행:

| KST | UTC | 설명 |
|-----|-----|------|
| 08:00 | 23:00 (전날) | 오전 카드뉴스 |
| 13:00 | 04:00 | 오후 카드뉴스 |

매 실행마다 40개 카드뉴스 생성 (5계정 × 8카테고리).

## 카테고리/계정 변경

서버의 `accounts.yaml`을 수정 후 컨테이너 재시작:

```bash
vi ~/cardnews/accounts.yaml
docker restart cardnews-app
```

## 트러블슈팅

```bash
# 컨테이너 내부 접속
docker exec -it cardnews-app bash

# cron 상태 확인
crontab -l

# cron 로그 확인
cat /app/logs/cron.log

# 수동 파이프라인 실행
cd /app && python main.py
```
