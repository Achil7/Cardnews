@echo off
chcp 65001 >nul
title Meme Cardnews - 초기 설치
echo ============================================
echo   Meme Cardnews 초기 설치
echo ============================================
echo.

cd /d "%~dp0"

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo https://www.python.org/downloads/ 에서 Python 3.11 이상을 설치하세요.
    echo 설치 시 "Add Python to PATH" 체크를 반드시 해주세요.
    pause
    exit /b 1
)

echo [1/4] 가상환경 생성 중...
if not exist ".venv" (
    python -m venv .venv
    echo   가상환경 생성 완료
) else (
    echo   가상환경 이미 존재
)

echo.
echo [2/4] 패키지 설치 중... (2~3분 소요)
.venv\Scripts\pip.exe install -r requirements.txt -q
.venv\Scripts\pip.exe install fastapi uvicorn python-multipart -q
echo   패키지 설치 완료

echo.
echo [3/4] Playwright 브라우저 설치 중... (3~5분 소요)
.venv\Scripts\python.exe -m playwright install chromium
echo   브라우저 설치 완료

echo.
echo [4/4] 데이터 디렉토리 생성...
if not exist "data" mkdir data
if not exist "data\output" mkdir data\output
echo   완료

echo.
echo ============================================
echo   설치 완료!
echo   run_gui.bat 를 더블클릭하여 실행하세요.
echo ============================================
pause
