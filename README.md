# Poomgo API Viewer

품고 Invoice API에서 데이터를 받아 브라우저 표로 출력하는 FastAPI 앱입니다.

## 실행

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
# .env의 POOMGO_API_KEY를 실제 키로 입력
uvicorn poomgo_viewer.app:app --reload
```

브라우저에서 `http://127.0.0.1:8000`을 열고 **새로고침**을 누르면 품고 API를 호출합니다.

- `GET /api/invoices`: 품고 API 응답을 그대로 반환
- 페이지와 페이지 크기는 서버가 자동으로 설정하며, 품고 기본 페이지 크기 20으로 전체 페이지를 자동 조회
- `closedAtGte`, `closedAtLte`: 송장 마감일시 시작/종료 범위
- 화면의 날짜는 한국시간 자정으로 해석해 API 요청 시 UTC ISO 형식으로 변환함. 예: `2026-09-12` → `2026-09-11T15:00:00.000Z`
- API 키는 서버에서만 사용하며 브라우저로 전달하지 않습니다.
- `MARIADB_DATABASE_URL`을 설정하면 조회 페이지를 받는 즉시 품목 정보를 MariaDB에 저장합니다.
- 송장 ID가 이미 저장되어 있으면 해당 송장과 품목은 건너뜁니다.
- 저장 테이블은 `poomgo_invoice` 하나이며, 품목의 `quantity`를 출고수량으로 저장합니다.
- 실행 결과는 로컬 `logs/poomgo_sync.log` 파일에 JSON Lines 형식으로 자동/수동 실행 유형, 상태, 처리 범위, 조회·저장·중복 건수, 오류 내용을 기록합니다.
- 로그는 기록 시점에 30일보다 오래된 항목을 자동 삭제합니다.
- 자동 저장은 기본 활성화되며 한국시간 `08:00`, `18:00`에 오늘 기준 3일 전 00시부터 2일 전 00시까지 조회합니다.
- 자동 저장을 끄려면 `AUTO_SYNC_ENABLED=false`로 설정합니다.
