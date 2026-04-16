import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import re
import shutil
from pathlib import Path
from collections import defaultdict

# ── 품번 정규식: ABC-123, ABC_123, ABC123 형태 감지
PRODUCT_CODE_RE = re.compile(r'([A-Za-z]{2,8})[-_]?(\d{2,5})', re.IGNORECASE)

VIDEO_EXTS = {'.mp4', '.mkv', '.avi', '.wmv', '.mov', '.m4v', '.ts', '.rmvb', '.flv'}
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
SUBTITLE_EXTS = {'.srt', '.ass', '.ssa', '.vtt', '.sub'}
ALL_EXTS = VIDEO_EXTS | IMAGE_EXTS | SUBTITLE_EXTS


def extract_product_code(filename: str):
    """파일명에서 품번 추출. 반환: (prefix, number, full_code) or None"""
    stem = Path(filename).stem
    m = PRODUCT_CODE_RE.search(stem)
    if m:
        prefix = m.group(1).upper()
        number = m.group(2).zfill(3)
        return prefix, number, f"{prefix}-{number}"
    return None


def scan_files(src_dir: str, exts: set, recursive: bool):
    """소스 폴더에서 파일 목록 수집"""
    src = Path(src_dir)
    pattern = '**/*' if recursive else '*'
    files = []
    for p in src.glob(pattern):
        if p.is_file() and p.suffix.lower() in exts:
            files.append(p)
    return files


def plan_moves(files: list, sort_mode: str):
    """
    sort_mode: 'title' (작품별) or 'prefix' (품번분류별)
    반환: [(src_path, dest_rel_folder, code_or_none), ...]
    """
    moves = []
    ungrouped = []
    for f in files:
        result = extract_product_code(f.name)
        if result:
            prefix, number, code = result
            if sort_mode == 'title':
                folder = code           # ABC-001
            else:
                folder = prefix         # ABC
            moves.append((f, folder, code))
        else:
            ungrouped.append((f, '_미분류', None))
    return moves, ungrouped


# ──────────────────────────────────────────────
# GUI
# ──────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AV 파일 정리기")
        self.resizable(True, True)
        self.minsize(680, 560)
        self._build_ui()
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = 720, 620
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ── UI 구성 ─────────────────────────────────
    def _build_ui(self):
        pad = dict(padx=10, pady=5)

        # ── 소스 폴더
        frm_src = ttk.LabelFrame(self, text=" 소스 폴더 (정리할 파일이 있는 곳) ")
        frm_src.pack(fill='x', **pad)
        self.src_var = tk.StringVar()
        ttk.Entry(frm_src, textvariable=self.src_var, width=60).pack(side='left', expand=True, fill='x', padx=(6,2), pady=6)
        ttk.Button(frm_src, text="찾아보기", command=self._pick_src).pack(side='left', padx=(0,6), pady=6)

        # ── 대상 폴더
        frm_dst = ttk.LabelFrame(self, text=" 대상 폴더 (정리된 파일이 이동할 곳) ")
        frm_dst.pack(fill='x', **pad)
        self.dst_var = tk.StringVar()
        ttk.Entry(frm_dst, textvariable=self.dst_var, width=60).pack(side='left', expand=True, fill='x', padx=(6,2), pady=6)
        ttk.Button(frm_dst, text="찾아보기", command=self._pick_dst).pack(side='left', padx=(0,6), pady=6)

        # ── 옵션
        frm_opt = ttk.LabelFrame(self, text=" 정렬 옵션 ")
        frm_opt.pack(fill='x', **pad)

        # 정렬 방식
        ttk.Label(frm_opt, text="정렬 방식:").grid(row=0, column=0, sticky='w', padx=8, pady=6)
        self.sort_var = tk.StringVar(value='title')
        cb = ttk.Combobox(frm_opt, textvariable=self.sort_var, state='readonly', width=22,
                          values=['title', 'prefix'])
        cb.grid(row=0, column=1, sticky='w', padx=4, pady=6)
        cb.bind('<<ComboboxSelected>>', self._on_sort_change)
        self.sort_label = ttk.Label(frm_opt, text="작품별  →  ABC-001/", foreground='gray')
        self.sort_label.grid(row=0, column=2, sticky='w', padx=10)

        # 파일 유형
        ttk.Label(frm_opt, text="파일 유형:").grid(row=1, column=0, sticky='w', padx=8, pady=4)
        self.chk_video = tk.BooleanVar(value=True)
        self.chk_image = tk.BooleanVar(value=False)
        self.chk_sub   = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm_opt, text="영상", variable=self.chk_video).grid(row=1, column=1, sticky='w', padx=4)
        ttk.Checkbutton(frm_opt, text="이미지", variable=self.chk_image).grid(row=1, column=2, sticky='w', padx=4)
        ttk.Checkbutton(frm_opt, text="자막", variable=self.chk_sub).grid(row=1, column=3, sticky='w', padx=4)

        # 하위 폴더 탐색 / 작업 방식
        self.chk_recursive = tk.BooleanVar(value=False)
        self.chk_copy      = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm_opt, text="하위 폴더 포함", variable=self.chk_recursive).grid(row=2, column=0, columnspan=2, sticky='w', padx=8, pady=4)
        ttk.Checkbutton(frm_opt, text="이동 대신 복사", variable=self.chk_copy).grid(row=2, column=2, columnspan=2, sticky='w', padx=4)

        # ── 버튼
        frm_btn = ttk.Frame(self)
        frm_btn.pack(fill='x', padx=10, pady=(4,0))
        ttk.Button(frm_btn, text="미리보기", command=self._preview).pack(side='left', padx=(0,6))
        ttk.Button(frm_btn, text="실행", command=self._execute).pack(side='left')
        self.status_lbl = ttk.Label(frm_btn, text="", foreground='blue')
        self.status_lbl.pack(side='left', padx=12)

        # ── 미리보기 트리
        frm_tree = ttk.LabelFrame(self, text=" 미리보기 ")
        frm_tree.pack(fill='both', expand=True, padx=10, pady=6)

        cols = ('src', 'arrow', 'dest')
        self.tree = ttk.Treeview(frm_tree, columns=cols, show='headings', height=14)
        self.tree.heading('src',   text='원본 파일명')
        self.tree.heading('arrow', text='')
        self.tree.heading('dest',  text='이동 경로')
        self.tree.column('src',   width=240, anchor='w')
        self.tree.column('arrow', width=30,  anchor='center')
        self.tree.column('dest',  width=360, anchor='w')

        vsb = ttk.Scrollbar(frm_tree, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        self.tree.tag_configure('ungrouped', foreground='gray')
        self.tree.tag_configure('grouped',   foreground='black')

        # 초기 콤보 레이블
        self._on_sort_change()

    # ── 이벤트 ──────────────────────────────────
    def _pick_src(self):
        d = filedialog.askdirectory(title="소스 폴더 선택")
        if d:
            self.src_var.set(d)

    def _pick_dst(self):
        d = filedialog.askdirectory(title="대상 폴더 선택")
        if d:
            self.dst_var.set(d)

    def _on_sort_change(self, *_):
        mode = self.sort_var.get()
        if mode == 'title':
            self.sort_label.config(text="작품별  →  ABC-001/")
        else:
            self.sort_label.config(text="품번분류별  →  ABC/")

    def _collect_exts(self):
        exts = set()
        if self.chk_video.get(): exts |= VIDEO_EXTS
        if self.chk_image.get(): exts |= IMAGE_EXTS
        if self.chk_sub.get():   exts |= SUBTITLE_EXTS
        return exts or VIDEO_EXTS   # 최소 영상은 포함

    def _validate(self):
        if not self.src_var.get():
            messagebox.showwarning("경고", "소스 폴더를 선택하세요.")
            return False
        if not self.dst_var.get():
            messagebox.showwarning("경고", "대상 폴더를 선택하세요.")
            return False
        if not Path(self.src_var.get()).is_dir():
            messagebox.showerror("오류", "소스 폴더가 존재하지 않습니다.")
            return False
        return True

    def _build_plan(self):
        exts = self._collect_exts()
        files = scan_files(self.src_var.get(), exts, self.chk_recursive.get())
        moves, ungrouped = plan_moves(files, self.sort_var.get())
        return moves, ungrouped

    def _preview(self):
        if not self._validate():
            return
        moves, ungrouped = self._build_plan()
        dst_base = self.dst_var.get()

        # 트리 초기화
        for item in self.tree.get_children():
            self.tree.delete(item)

        count = 0
        for src, folder, code in moves:
            dest = str(Path(dst_base) / folder / src.name)
            self.tree.insert('', 'end', values=(src.name, '→', dest), tags=('grouped',))
            count += 1
        for src, folder, _ in ungrouped:
            dest = str(Path(dst_base) / folder / src.name)
            self.tree.insert('', 'end', values=(src.name, '→', dest), tags=('ungrouped',))
            count += 1

        total_ung = len(ungrouped)
        self.status_lbl.config(
            text=f"총 {count}개 파일  |  미분류 {total_ung}개",
            foreground='blue'
        )

    def _execute(self):
        if not self._validate():
            return
        moves, ungrouped = self._build_plan()
        if not moves and not ungrouped:
            messagebox.showinfo("알림", "대상 파일이 없습니다.")
            return

        action = "복사" if self.chk_copy.get() else "이동"
        total = len(moves) + len(ungrouped)
        ok = messagebox.askyesno("확인", f"총 {total}개 파일을 {action}하시겠습니까?")
        if not ok:
            return

        dst_base = Path(self.dst_var.get())
        errors = []
        done = 0

        all_items = [(s, f) for s, f, _ in moves] + [(s, f) for s, f, _ in ungrouped]
        for src, folder in all_items:
            dest_dir = dst_base / folder
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_file = dest_dir / src.name

            # 중복 파일명 처리
            if dest_file.exists():
                stem = src.stem
                suffix = src.suffix
                i = 1
                while dest_file.exists():
                    dest_file = dest_dir / f"{stem}_{i}{suffix}"
                    i += 1
            try:
                if self.chk_copy.get():
                    shutil.copy2(str(src), str(dest_file))
                else:
                    shutil.move(str(src), str(dest_file))
                done += 1
            except Exception as e:
                errors.append(f"{src.name}: {e}")

        if errors:
            err_msg = '\n'.join(errors[:10])
            if len(errors) > 10:
                err_msg += f'\n... 외 {len(errors)-10}개'
            messagebox.showerror("오류 발생", f"{done}개 완료, {len(errors)}개 실패\n\n{err_msg}")
        else:
            messagebox.showinfo("완료", f"{done}개 파일 {action} 완료!")
            self.status_lbl.config(text=f"{done}개 {action} 완료", foreground='green')
            self._preview()  # 결과 갱신


if __name__ == '__main__':
    app = App()
    app.mainloop()
