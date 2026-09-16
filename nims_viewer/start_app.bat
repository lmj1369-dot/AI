@echo off
setlocal
cd /d "%~dp0"

if not exist ".env" if exist ".env.example" (
  copy ".env.example" ".env" >nul
  echo .env.example 을 기반으로 .env 를 생성했습니다.
)

if exist ".venv\Scripts\python.exe" (
  echo NIMS 뷰어를 실행합니다...
  call ".venv\Scripts\python.exe" "src\nims_viewer\gui_app.py"
  exit /b %ERRORLEVEL%
)

if exist "dist\NimsViewer.exe" (
  echo EXE 실행 파일을 실행합니다...
  start "" "%~dp0dist\NimsViewer.exe"
  exit /b 0
)

color 0c
echo 실행 환경을 찾지 못했습니다.
 echo .venv 또는 dist\NimsViewer.exe 가 필요합니다.
 echo 먼저 빌드 스크립트를 실행해 주세요.
pause
exit /b 1
