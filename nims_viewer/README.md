# NIMS 마약류취급자 정보 조회기 (Nims Viewer)

NIMS(마약류통합관리시스템)에서 제공하는 마약류취급자 정보 조회 API(`bsshinfo_st_v1.do`)를 활용하여 사업자번호 및 요양기관기호로 거래처 정보를 확인하고, **가입허가 및 정상 상태인 마약류취급자 식별번호**를 직관적으로 확인할 수 있는 Windows 데스크톱 응용프로그램입니다.

## 주요 기능

1. **마약류취급자 정보 조회**: 사업자등록번호(10자리), 요양기관기호, 업체명 등으로 실시간 조회
2. **핵심 식별번호 하이라이트**: `회원가입여부 == '가입'` 및 `상태 == '정상'`인 마약류취급자 식별번호(`BSSH_CD`)를 상단 카드에 강조 표시 및 원클릭 복사 기능 제공
3. **상세 데이터 그리드**: 전체 결과 리스트를 한눈에 볼 수 있는 그리드 테이블 및 엑셀 붙여넣기용 TSV 복사 기능
4. **인증키(K) 관리**: UI 설정 창에서 NIMS API 연계 인증키를 간편하게 등록 및 `.env`에 안전하게 저장

## 실행 및 빌드 방법

### Python 스크립트로 실행
```powershell
c:/AIproject/.venv/Scripts/python.exe -m nims_viewer.gui_app
```

### EXE 단일 실행 파일 빌드
```powershell
c:/AIproject/.venv/Scripts/python.exe build_exe.py
```
빌드 완료 후 `dist/NimsViewer.exe` 파일이 생성됩니다.
