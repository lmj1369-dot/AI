import json
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

from nims_viewer.client import NimsClient
from nims_viewer.config import Settings, get_settings, resolve_env_path


class NimsGuiApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("동국제약 NIMS 마약류취급자 정보 조회")
        self.root.geometry("1100x700")
        self.root.minsize(900, 550)

        self.settings: Settings = get_settings()
        self.client = NimsClient(
            api_key=self.settings.nims_api_key,
            api_url=self.settings.nims_api_url,
            timeout=self.settings.nims_timeout_seconds,
        )

        self.current_items: list[dict[str, Any]] = []
        self.valid_codes: list[dict[str, str]] = []

        self._setup_styles()
        self._build_ui()
        self._update_key_status()

    def _setup_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # 동국제약 컬러 팔레트
        self.COLOR_PRIMARY = "#123d6b"      # 딥 네이비
        self.COLOR_ACCENT = "#2b8fd9"       # 세련된 블루
        self.COLOR_SECONDARY = "#9ccf3f"    # 라이트 그린
        self.COLOR_BG = "#f3f6fb"
        self.COLOR_CARD = "#ffffff"
        self.COLOR_MUTED = "#67788d"
        self.COLOR_SUCCESS_BG = "#edf9f1"
        self.COLOR_SUCCESS_BORDER = "#2aa26a"
        self.COLOR_SUCCESS_TEXT = "#0b5c3a"

        self.root.configure(bg=self.COLOR_BG)

        style.configure("TLabel", background=self.COLOR_BG, foreground=self.COLOR_PRIMARY, font=("맑은 고딕", 9))
        style.configure("Header.TLabel", background=self.COLOR_PRIMARY, foreground="#ffffff", font=("맑은 고딕", 12, "bold"))
        style.configure("SubHeader.TLabel", background=self.COLOR_PRIMARY, foreground="#dfeaf7", font=("맑은 고딕", 9))
        style.configure("Card.TFrame", background=self.COLOR_CARD)

        style.configure("Primary.TButton", font=("맑은 고딕", 9, "bold"), background=self.COLOR_PRIMARY, foreground="#ffffff")
        style.map("Primary.TButton", background=[("active", "#0d2d52"), ("disabled", "#b3bfd0")])

        # Treeview 스타일
        style.configure("Treeview.Heading", font=("맑은 고딕", 9, "bold"), background="#dfeaf7", foreground="#16385d")
        style.configure("Treeview", font=("맑은 고딕", 9), rowheight=28)
        style.map("Treeview", background=[("selected", "#d7ebff")], foreground=[("selected", "#123d6b")])

    def _build_ui(self) -> None:
        # 1. 상단 헤더
        header_frame = tk.Frame(self.root, bg=self.COLOR_PRIMARY, height=54)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)

        header_inner = tk.Frame(header_frame, bg=self.COLOR_PRIMARY)
        header_inner.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        title_lbl = tk.Label(
            header_inner,
            text="동국제약  NIMS 마약류취급자 정보 조회",
            font=("맑은 고딕", 12, "bold"),
            bg=self.COLOR_PRIMARY,
            foreground="#ffffff",
        )
        title_lbl.pack(side=tk.LEFT, padx=(4, 0))

        key_btn = tk.Button(
            header_inner,
            text="⚙️ API 인증키 설정",
            command=self._open_key_dialog,
            bg="#ffffff",
            fg=self.COLOR_PRIMARY,
            font=("맑은 고딕", 9, "bold"),
            relief=tk.FLAT,
            padx=10,
            cursor="hand2",
        )
        key_btn.pack(side=tk.RIGHT, padx=(8, 0))

        self.key_status_lbl = tk.Label(
            header_inner,
            text="인증키 확인 중...",
            font=("맑은 고딕", 9),
            bg=self.COLOR_PRIMARY,
            fg="#93c5fd",
        )
        self.key_status_lbl.pack(side=tk.RIGHT)

        # 메인 컨테이너
        main_container = tk.Frame(self.root, bg=self.COLOR_BG)
        main_container.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        # 2. 검색 입력 카드
        search_card = tk.LabelFrame(
            main_container,
            text=" 조회 조건 입력 ",
            font=("맑은 고딕", 9, "bold"),
            bg=self.COLOR_CARD,
            fg=self.COLOR_PRIMARY,
            padx=12,
            pady=10,
        )
        search_card.pack(fill=tk.X, pady=(0, 10))

        input_row = tk.Frame(search_card, bg=self.COLOR_CARD)
        input_row.pack(fill=tk.X)

        tk.Label(input_row, text="사업자등록번호:", bg=self.COLOR_CARD, font=("맑은 고딕", 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.bizrno_var = tk.StringVar()
        self.bizrno_entry = tk.Entry(input_row, textvariable=self.bizrno_var, width=16, font=("맑은 고딕", 10))
        self.bizrno_entry.pack(side=tk.LEFT, padx=(0, 16))
        self.bizrno_entry.bind("<Return>", lambda _: self._on_search())
        self.bizrno_entry.bind("<KeyRelease>", self._format_bizrno_input)

        tk.Label(input_row, text="요양기관기호:", bg=self.COLOR_CARD, font=("맑은 고딕", 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.hptl_no_var = tk.StringVar()
        self.hptl_no_entry = tk.Entry(input_row, textvariable=self.hptl_no_var, width=14, font=("맑은 고딕", 10))
        self.hptl_no_entry.pack(side=tk.LEFT, padx=(0, 16))
        self.hptl_no_entry.bind("<Return>", lambda _: self._on_search())

        tk.Label(input_row, text="업체명:", bg=self.COLOR_CARD).pack(side=tk.LEFT, padx=(0, 4))
        self.bssh_nm_var = tk.StringVar()
        self.bssh_nm_entry = tk.Entry(input_row, textvariable=self.bssh_nm_var, width=14, font=("맑은 고딕", 10))
        self.bssh_nm_entry.pack(side=tk.LEFT, padx=(0, 16))
        self.bssh_nm_entry.bind("<Return>", lambda _: self._on_search())

        self.search_btn = tk.Button(
            input_row,
            text="🔍 조회하기",
            command=self._on_search,
            bg=self.COLOR_PRIMARY,
            fg="#ffffff",
            font=("맑은 고딕", 9, "bold"),
            relief=tk.FLAT,
            padx=16,
            pady=4,
            cursor="hand2",
        )
        self.search_btn.pack(side=tk.LEFT, padx=(0, 6))

        reset_btn = tk.Button(
            input_row,
            text="초기화",
            command=self._on_reset,
            bg="#f1f5f9",
            fg="#334155",
            font=("맑은 고딕", 9),
            relief=tk.GROOVE,
            padx=10,
            pady=4,
            cursor="hand2",
        )
        reset_btn.pack(side=tk.LEFT)

        # 3. 핵심 결과 하이라이트 박스 (가입허가 & 정상 상태 식별번호 표시)
        self.highlight_frame = tk.Frame(
            main_container,
            bg=self.COLOR_SUCCESS_BG,
            highlightbackground=self.COLOR_SUCCESS_BORDER,
            highlightthickness=2,
            padx=14,
            pady=10,
        )
        self.highlight_frame.pack(fill=tk.X, pady=(0, 10))

        hl_top_row = tk.Frame(self.highlight_frame, bg=self.COLOR_SUCCESS_BG)
        hl_top_row.pack(fill=tk.X)

        self.hl_badge_lbl = tk.Label(
            hl_top_row,
            text="✓ 가입허가 & 정상 상태 마약류취급자 식별번호",
            font=("맑은 고딕", 9, "bold"),
            bg=self.COLOR_SUCCESS_TEXT,
            fg="#ffffff",
            padx=6,
            pady=2,
        )
        self.hl_badge_lbl.pack(side=tk.LEFT)

        self.hl_count_lbl = tk.Label(
            hl_top_row,
            text="",
            font=("맑은 고딕", 9),
            bg=self.COLOR_SUCCESS_BG,
            fg=self.COLOR_SUCCESS_TEXT,
        )
        self.hl_count_lbl.pack(side=tk.LEFT, padx=(8, 0))

        self.hl_body_frame = tk.Frame(self.highlight_frame, bg=self.COLOR_SUCCESS_BG)
        self.hl_body_frame.pack(fill=tk.X, pady=(6, 0))

        self.hl_main_lbl = tk.Label(
            self.hl_body_frame,
            text="사업자번호 또는 요양기관기호 입력 후 조회하세요.",
            font=("맑은 고딕", 12, "bold"),
            bg=self.COLOR_SUCCESS_BG,
            fg="#334155",
        )
        self.hl_main_lbl.pack(side=tk.LEFT)

        self.copy_main_code_btn = tk.Button(
            self.hl_body_frame,
            text="📋 식별번호 복사",
            command=self._copy_highlight_code,
            bg=self.COLOR_PRIMARY,
            fg="#ffffff",
            font=("맑은 고딕", 9, "bold"),
            relief=tk.FLAT,
            padx=10,
            cursor="hand2",
            state=tk.DISABLED,
        )
        self.copy_main_code_btn.pack(side=tk.RIGHT)

        # 4. 결과 그리드 테이블
        grid_card = tk.LabelFrame(
            main_container,
            text=" 전체 조회 결과 목록 ",
            font=("맑은 고딕", 9, "bold"),
            bg=self.COLOR_CARD,
            fg=self.COLOR_PRIMARY,
            padx=8,
            pady=6,
        )
        grid_card.pack(fill=tk.BOTH, expand=True)

        toolbar = tk.Frame(grid_card, bg=self.COLOR_CARD)
        toolbar.pack(fill=tk.X, pady=(0, 4))

        self.status_bar_lbl = tk.Label(
            toolbar,
            text="대기 중",
            font=("맑은 고딕", 9),
            bg=self.COLOR_CARD,
            fg="#64748b",
        )
        self.status_bar_lbl.pack(side=tk.LEFT)

        self.copy_all_btn = tk.Button(
            toolbar,
            text="📋 엑셀 붙여넣기용 전체 복사",
            command=self._copy_all_tsv,
            bg="#f1f5f9",
            fg="#1e293b",
            font=("맑은 고딕", 8),
            relief=tk.GROOVE,
            padx=8,
            cursor="hand2",
            state=tk.DISABLED,
        )
        self.copy_all_btn.pack(side=tk.RIGHT)

        # Treeview 설정
        columns = [
            ("status_eval", "상태판정", 70, "center"),
            ("bssh_cd", "취급자식별번호", 110, "center"),
            ("bssh_nm", "업체명", 160, "w"),
            ("rprsntv_nm", "대표자명", 80, "center"),
            ("bizrno", "사업자등록번호", 110, "center"),
            ("hptl_no", "요양기관기호", 100, "center"),
            ("join_yn", "회원가입", 70, "center"),
            ("bssh_sttus_nm", "상태", 70, "center"),
            ("induty_nm", "업종명", 110, "w"),
            ("hdnt_nm", "의료업자구분", 100, "w"),
            ("chrg_nm", "담당자명", 80, "center"),
            ("prmisn_no", "허가번호", 100, "w"),
        ]

        tree_frame = tk.Frame(grid_card, bg=self.COLOR_CARD)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=[col[0] for col in columns],
            show="headings",
            selectmode="browse",
        )

        for col_id, col_name, width, anchor in columns:
            self.tree.heading(col_id, text=col_name)
            self.tree.column(col_id, width=width, anchor=anchor, minwidth=50)

        # 스크롤바
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # 행 색상 태그
        self.tree.tag_configure("valid_row", background="#f0fdf4")
        self.tree.tag_configure("invalid_row", background="#ffffff")

        self.bizrno_entry.focus()

    def _format_bizrno_input(self, _event: Any) -> None:
        raw = "".join(filter(str.isdigit, self.bizrno_var.get()))[:10]
        if len(raw) > 5:
            formatted = f"{raw[:3]}-{raw[3:5]}-{raw[5:]}"
        elif len(raw) > 3:
            formatted = f"{raw[:3]}-{raw[3:]}"
        else:
            formatted = raw
        if self.bizrno_var.get() != formatted:
            self.bizrno_var.set(formatted)
            self.bizrno_entry.icursor(tk.END)

    def _update_key_status(self) -> None:
        self.settings = get_settings()
        key = self.settings.nims_api_key.strip()
        if key:
            masked = key[:4] + "*" * max(0, len(key) - 8) + key[-4:] if len(key) > 8 else "***"
            self.key_status_lbl.config(text=f"인증키: {masked} (정상)", fg="#86efac")
            self.client.api_key = key
        else:
            self.key_status_lbl.config(text="인증키 미등록 (설정 필요 ⚠️)", fg="#fca5a5")

    def _open_key_dialog(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("NIMS API 인증키 설정")
        dialog.geometry("420x190")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        frame = tk.Frame(dialog, padx=16, pady=16, bg="#ffffff")
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            frame,
            text="NIMS API 인증키(K)를 입력하세요:",
            font=("맑은 고딕", 9, "bold"),
            bg="#ffffff",
        ).pack(anchor="w", pady=(0, 6))

        key_entry = tk.Entry(frame, font=("맑은 고딕", 10), width=40)
        key_entry.pack(fill=tk.X, pady=(0, 12))
        if self.settings.nims_api_key:
            key_entry.insert(0, self.settings.nims_api_key)

        def save_key() -> None:
            new_key = key_entry.get().strip()
            if not new_key:
                messagebox.showwarning("입력 오류", "인증키를 입력해주세요.", parent=dialog)
                return

            env_path = resolve_env_path()
            env_path.parent.mkdir(parents=True, exist_ok=True)
            lines: list[str] = []
            if env_path.exists():
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    if not line.startswith("NIMS_API_KEY="):
                        lines.append(line)
            lines.append(f"NIMS_API_KEY={new_key}")
            env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

            get_settings.cache_clear()
            self._update_key_status()
            messagebox.showinfo("저장 완료", "인증키가 안전하게 저장되었습니다.", parent=dialog)
            dialog.destroy()

        btn_row = tk.Frame(frame, bg="#ffffff")
        btn_row.pack(fill=tk.X, pady=(8, 0))

        tk.Button(
            btn_row,
            text="저장",
            command=save_key,
            bg=self.COLOR_PRIMARY,
            fg="#ffffff",
            font=("맑은 고딕", 9, "bold"),
            padx=14,
            relief=tk.FLAT,
            cursor="hand2",
        ).pack(side=tk.RIGHT, padx=(6, 0))

        tk.Button(
            btn_row,
            text="취소",
            command=dialog.destroy,
            bg="#f1f5f9",
            fg="#334155",
            font=("맑은 고딕", 9),
            padx=10,
            relief=tk.GROOVE,
            cursor="hand2",
        ).pack(side=tk.RIGHT)

    def _on_reset(self) -> None:
        self.bizrno_var.set("")
        self.hptl_no_var.set("")
        self.bssh_nm_var.set("")
        self.tree.delete(*self.tree.get_children())
        self.current_items = []
        self.valid_codes = []

        self.highlight_frame.config(bg=self.COLOR_SUCCESS_BG, highlightbackground=self.COLOR_SUCCESS_BORDER)
        self.hl_badge_lbl.config(text="✓ 가입허가 & 정상 상태 마약류취급자 식별번호", bg=self.COLOR_SUCCESS_TEXT)
        self.hl_count_lbl.config(text="")
        self.hl_main_lbl.config(text="사업자번호 또는 요양기관기호 입력 후 조회하세요.", fg="#334155", font=("맑은 고딕", 12, "bold"))
        self.copy_main_code_btn.config(state=tk.DISABLED)
        self.copy_all_btn.config(state=tk.DISABLED)
        self.status_bar_lbl.config(text="대기 중", fg="#64748b")
        self.bizrno_entry.focus()

    def _on_search(self) -> None:
        bizrno = self.bizrno_var.get().strip()
        hptl_no = self.hptl_no_var.get().strip()
        bssh_nm = self.bssh_nm_var.get().strip()

        if not bizrno and not hptl_no and not bssh_nm:
            messagebox.showwarning("입력 필요", "사업자등록번호 또는 요양기관기호를 최소 1개 이상 입력해주세요.")
            self.bizrno_entry.focus()
            return

        if not self.settings.nims_api_key.strip():
            messagebox.showwarning("인증키 누락", "NIMS API 인증키가 등록되지 않았습니다.\n우측 상단 [API 인증키 설정]에서 키를 등록해주세요.")
            self._open_key_dialog()
            return

        # UI 로딩 상태 변경
        self.search_btn.config(state=tk.DISABLED, text="⏳ 조회 중...")
        self.status_bar_lbl.config(text="NIMS 서버와 통신 중...", fg=self.COLOR_ACCENT)
        self.tree.delete(*self.tree.get_children())

        # 백그라운드 스레드에서 API 호출 (UI 멈춤 방지)
        threading.Thread(target=self._search_worker, args=(bizrno, hptl_no, bssh_nm), daemon=True).start()

    def _search_worker(self, bizrno: str, hptl_no: str, bssh_nm: str) -> None:
        try:
            result = self.client.search_bssh_sync(
                bizrno=bizrno,
                hptl_no=hptl_no,
                bssh_nm=bssh_nm,
            )
            self.root.after(0, self._render_results, result)
        except Exception as error:
            self.root.after(0, self._render_error, str(error))

    def _render_error(self, error_msg: str) -> None:
        self.search_btn.config(state=tk.NORMAL, text="🔍 조회하기")
        self.status_bar_lbl.config(text=f"오류: {error_msg}", fg="#dc2626")

        self.highlight_frame.config(bg="#fef2f2", highlightbackground="#fca5a5")
        if "인증키" in error_msg:
            label_text = "⚠️ 인증키 오류"
        elif "인터넷 연결" in error_msg or "연결" in error_msg or "응답 시간이 초과" in error_msg:
            label_text = "⚠️ 네트워크 오류"
        else:
            label_text = "⚠️ 조회 오류"

        self.hl_badge_lbl.config(text=label_text, bg="#dc2626")
        self.hl_count_lbl.config(text="")
        self.hl_main_lbl.config(text=error_msg, fg="#991b1b", font=("맑은 고딕", 10))
        self.copy_main_code_btn.config(state=tk.DISABLED)
        self.copy_all_btn.config(state=tk.DISABLED)

    def _render_results(self, data: dict[str, Any]) -> None:
        self.search_btn.config(state=tk.NORMAL, text="🔍 조회하기")
        items = data.get("items", [])
        valid_list = data.get("valid_bssh_list", [])
        self.current_items = items
        self.valid_codes = valid_list

        total_cnt = len(items)
        self.status_bar_lbl.config(
            text=f"총 {total_cnt}건 조회 완료 (NIMS 응답: {data.get('result_msg', '정상')})",
            fg="#1e293b",
        )

        # 1. 하이라이트 카드 렌더링
        if valid_list:
            self.highlight_frame.config(bg=self.COLOR_SUCCESS_BG, highlightbackground=self.COLOR_SUCCESS_BORDER)
            self.hl_badge_lbl.config(text="✓ 가입허가 & 정상 상태 마약류취급자 식별번호", bg=self.COLOR_SUCCESS_TEXT)
            self.hl_count_lbl.config(text=f"(정상 {len(valid_list)}건)")

            main_target = valid_list[0]
            display_text = f"【 {main_target['bssh_cd']} 】  -  {main_target['bssh_nm']}"
            if len(valid_list) > 1:
                display_text += f" (외 {len(valid_list)-1}건)"

            self.hl_main_lbl.config(
                text=display_text,
                fg=self.COLOR_PRIMARY,
                font=("맑은 고딕", 14, "bold"),
            )
            self.copy_main_code_btn.config(state=tk.NORMAL)
        else:
            self.highlight_frame.config(bg="#fef2f2", highlightbackground="#fca5a5")
            self.hl_badge_lbl.config(text="⚠️ 정상 식별번호 없음", bg="#dc2626")
            self.hl_count_lbl.config(text="")
            self.hl_main_lbl.config(
                text="조회된 결과 중 회원가입 및 정상 상태인 식별번호가 없습니다. (미가입/폐업 여부 확인 필요)",
                fg="#991b1b",
                font=("맑은 고딕", 10, "bold"),
            )
            self.copy_main_code_btn.config(state=tk.DISABLED)

        # 2. 그리드 렌더링
        self.tree.delete(*self.tree.get_children())
        for item in items:
            is_valid = item.get("is_active_valid", False)
            tag = "valid_row" if is_valid else "invalid_row"
            status_text = "✓ 정상승인" if is_valid else "확인필요"

            bizrno_fmt = item.get("bizrno", "")
            if len(bizrno_fmt) == 10:
                bizrno_fmt = f"{bizrno_fmt[:3]}-{bizrno_fmt[3:5]}-{bizrno_fmt[5:]}"

            self.tree.insert(
                "",
                tk.END,
                values=(
                    status_text,
                    item.get("bssh_cd", "-"),
                    item.get("bssh_nm", "-"),
                    item.get("rprsntv_nm", "-"),
                    bizrno_fmt or "-",
                    item.get("hptl_no", "-"),
                    item.get("join_yn", "-"),
                    item.get("bssh_sttus_nm", "-"),
                    item.get("induty_nm", "-"),
                    item.get("hdnt_nm", "-"),
                    item.get("chrg_nm", "-"),
                    item.get("prmisn_no", "-"),
                ),
                tags=(tag,),
            )

        self.copy_all_btn.config(state=tk.NORMAL if items else tk.DISABLED)

    def _copy_highlight_code(self) -> None:
        if not self.valid_codes:
            return
        code = self.valid_codes[0]["bssh_cd"]
        self.root.clipboard_clear()
        self.root.clipboard_append(code)
        messagebox.showinfo("복사 완료", f"마약류취급자 식별번호가 복사되었습니다.\n\n▶ {code}")

    def _copy_all_tsv(self) -> None:
        if not self.current_items:
            return
        headers = ["상태판정", "취급자식별번호", "업체명", "대표자명", "사업자등록번호", "요양기관기호", "회원가입여부", "상태", "업종명", "의료업자구분", "담당자명", "허가번호"]
        rows = []
        for r in self.current_items:
            status_eval = "정상승인" if r.get("is_active_valid") else "확인필요"
            rows.append([
                status_eval,
                r.get("bssh_cd", ""),
                r.get("bssh_nm", ""),
                r.get("rprsntv_nm", ""),
                r.get("bizrno", ""),
                r.get("hptl_no", ""),
                r.get("join_yn", ""),
                r.get("bssh_sttus_nm", ""),
                r.get("induty_nm", ""),
                r.get("hdnt_nm", ""),
                r.get("chrg_nm", ""),
                r.get("prmisn_no", ""),
            ])
        tsv = "\t".join(headers) + "\n" + "\n".join("\t".join(str(c) for c in row) for row in rows)
        self.root.clipboard_clear()
        self.root.clipboard_append(tsv)
        messagebox.showinfo("복사 완료", f"조회된 {len(self.current_items)}건의 전체 데이터가 클립보드에 복사되었습니다.\n엑셀(Excel)에 [Ctrl + V]로 붙여넣으세요.")


def main() -> None:
    root = tk.Tk()
    app = NimsGuiApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
