#!/usr/bin/env python3
"""PDF Editor Lite - Fast, lightweight PDF editor. No thumbnails, instant loading."""

import io
import os
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog


def _check_deps():
    try:
        __import__("PyPDF2")
    except ImportError:
        print("Installing PyPDF2...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyPDF2"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


_check_deps()
from PyPDF2 import PdfReader, PdfWriter

BG = "#1b2838"
BG2 = "#1e3044"
FG = "#c8d6e5"
FG2 = "#7f8fa6"
ACCENT = "#0984e3"
SEL_BG = "#0652DD"
WHITE = "#ffffff"


class PDFEditorLite:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Editor Lite")
        self.root.geometry("700x550")
        self.root.minsize(500, 400)
        self.root.configure(bg=BG)

        self.reader = None
        self.loaded_path = None
        self.original_path = None
        self.modified = False

        self._build_ui()

    def _btn(self, parent, text, cmd, bg=BG2, fg=FG):
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                      activebackground=ACCENT, activeforeground=WHITE,
                      relief="flat", font=("Segoe UI", 9), padx=8, pady=3,
                      cursor="hand2", bd=0, highlightthickness=0)
        b.bind("<Enter>", lambda e: b.config(bg=ACCENT))
        b.bind("<Leave>", lambda e: b.config(bg=bg))
        return b

    def _build_ui(self):
        # Toolbar
        tb = tk.Frame(self.root, bg=BG, padx=8, pady=6)
        tb.pack(fill=tk.X)

        self._btn(tb, "\u25A4 Open", self.open_pdf, bg=ACCENT, fg=WHITE).pack(side=tk.LEFT, padx=2)
        self._btn(tb, "Save", self.save).pack(side=tk.LEFT, padx=2)
        self._btn(tb, "Save As", self.save_as).pack(side=tk.LEFT, padx=2)

        tk.Frame(tb, width=1, bg="#2d4560").pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)

        self._btn(tb, "\u21BB CW", lambda: self.rotate(90)).pack(side=tk.LEFT, padx=2)
        self._btn(tb, "\u21BA CCW", lambda: self.rotate(270)).pack(side=tk.LEFT, padx=2)
        self._btn(tb, "180\u00B0", lambda: self.rotate(180)).pack(side=tk.LEFT, padx=2)
        self._btn(tb, "Auto", self.auto_rotate).pack(side=tk.LEFT, padx=2)

        tk.Frame(tb, width=1, bg="#2d4560").pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)

        self._btn(tb, "\u2716 Del", self.delete_pages, bg="#3a1520", fg="#ff6b6b").pack(side=tk.LEFT, padx=2)
        self._btn(tb, "Merge", self.merge).pack(side=tk.LEFT, padx=2)
        self._btn(tb, "Split", self.split_pages).pack(side=tk.LEFT, padx=2)
        self._btn(tb, "Split Size", self.split_size).pack(side=tk.LEFT, padx=2)

        # File info
        info = tk.Frame(self.root, bg=BG, padx=10)
        info.pack(fill=tk.X)
        self.file_label = tk.Label(info, text="No file loaded", bg=BG, fg=FG2, font=("Segoe UI", 10))
        self.file_label.pack(side=tk.LEFT)
        self.sel_label = tk.Label(info, text="", bg=BG, fg=ACCENT, font=("Segoe UI", 9))
        self.sel_label.pack(side=tk.RIGHT)

        # Page list
        list_frame = tk.Frame(self.root, bg=BG, padx=8, pady=4)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED,
                                   bg=BG2, fg=FG, selectbackground=SEL_BG, selectforeground=WHITE,
                                   font=("Consolas", 10), relief="flat", bd=0,
                                   highlightthickness=1, highlightcolor=ACCENT, highlightbackground="#2d4560")
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox.bind("<<ListboxSelect>>", lambda e: self._update_sel())

        # Status bar
        status = tk.Frame(self.root, bg="#0c1620", height=24)
        status.pack(fill=tk.X, side=tk.BOTTOM)
        status.pack_propagate(False)
        self.status = tk.Label(status, text="  Ctrl+O Open | Ctrl+A Select All | Del Delete | Ctrl+S Save",
                               bg="#0c1620", fg=FG2, font=("Segoe UI", 8))
        self.status.pack(side=tk.LEFT, padx=6)

        # Keys
        self.root.bind("<Control-o>", lambda e: self.open_pdf())
        self.root.bind("<Control-a>", lambda e: self.listbox.select_set(0, tk.END))
        self.root.bind("<Delete>", lambda e: self.delete_pages())
        self.root.bind("<Control-s>", lambda e: self.save())

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        if not self.reader: return
        for i, page in enumerate(self.reader.pages):
            box = page.mediabox
            w, h = float(box.width), float(box.height)
            rot = page.get("/Rotate", 0)
            line = f"  Page {i+1:>4d}    {w:.0f} x {h:.0f} pt"
            if rot: line += f"    rot {rot}\u00B0"
            self.listbox.insert(tk.END, line)

    def _update_sel(self):
        sel = self.listbox.curselection()
        total = self.listbox.size()
        if sel:
            self.sel_label.config(text=f"{len(sel)}/{total} selected")
        else:
            self.sel_label.config(text=f"{total} pages" if total else "")

    def _get_sel(self):
        sel = self.listbox.curselection()
        if not sel: messagebox.showinfo("Info", "Select pages in the list first.")
        return sel

    def _need_pdf(self):
        if not self.reader: messagebox.showinfo("Info", "Open a PDF first."); return False
        return True

    # ── File ──

    def open_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf"), ("All", "*.*")])
        if not path: return
        try:
            self.reader = PdfReader(path)
            self.loaded_path = path
            self.original_path = path
            self.modified = False
            name = os.path.basename(path)
            self.file_label.config(text=f"\u25CF  {name}  ({len(self.reader.pages)} pages)", fg=FG)
            self.root.title(f"PDF Editor Lite - {name}")
            self._refresh_list()
            self.status.config(text=f"  Opened {name}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def save(self):
        if not self._need_pdf(): return
        if not self.original_path: self.save_as(); return
        if not self.modified: messagebox.showinfo("Save", "No changes."); return
        if not messagebox.askyesno("Save", f"Overwrite?\n{self.original_path}"): return
        w = PdfWriter()
        for p in self.reader.pages: w.add_page(p)
        with open(self.original_path, "wb") as f: w.write(f)
        self._load(self.original_path)
        self.status.config(text=f"  Saved")

    def save_as(self):
        if not self._need_pdf(): return
        name = os.path.basename(self.original_path) if self.original_path else "output.pdf"
        out = filedialog.asksaveasfilename(defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")], initialfile=name)
        if not out: return
        w = PdfWriter()
        for p in self.reader.pages: w.add_page(p)
        with open(out, "wb") as f: w.write(f)
        self._load(out)
        self.status.config(text=f"  Saved to {os.path.basename(out)}")

    # ── Edit ──

    def rotate(self, deg):
        if not self._need_pdf(): return
        sel = self._get_sel()
        if not sel: return
        w = PdfWriter()
        for i, p in enumerate(self.reader.pages):
            if i in sel: p = p.rotate(deg)
            w.add_page(p)
        self._apply(w)
        self.status.config(text=f"  Rotated {len(sel)} page(s) {deg}\u00B0")

    def auto_rotate(self):
        if not self._need_pdf(): return
        w = PdfWriter(); count = 0
        for p in self.reader.pages:
            box = p.mediabox
            if float(box.width) > float(box.height): p = p.rotate(90); count += 1
            w.add_page(p)
        self._apply(w)
        self.status.config(text=f"  Auto-rotated {count} page(s)")

    def delete_pages(self):
        if not self._need_pdf(): return
        sel = self._get_sel()
        if not sel: return
        if not messagebox.askyesno("Delete", f"Delete {len(sel)} page(s)?"): return
        w = PdfWriter()
        for i, p in enumerate(self.reader.pages):
            if i not in sel: w.add_page(p)
        if not w.pages: messagebox.showwarning("Warning", "Can't delete all."); return
        self._apply(w)
        self.status.config(text=f"  Deleted {len(sel)} page(s)")

    def merge(self):
        paths = filedialog.askopenfilenames(title="Select PDFs (Ctrl+Click)", filetypes=[("PDF", "*.pdf")])
        if not paths: return
        w = PdfWriter()
        if self.reader:
            for p in self.reader.pages: w.add_page(p)
        for path in paths:
            try:
                r = PdfReader(path)
                for p in r.pages: w.add_page(p)
            except Exception as e:
                messagebox.showerror("Error", str(e)); return
        out = filedialog.asksaveasfilename(defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")], initialfile="merged.pdf")
        if not out: return
        with open(out, "wb") as f: w.write(f)
        self._load(out)
        self.status.config(text=f"  Merged {len(w.pages)} pages")

    def split_pages(self):
        if not self._need_pdf(): return
        total = len(self.reader.pages)
        result = simpledialog.askstring("Split", f"{total} pages\n\nRanges: 1-3, 4-6\nEvery N: 3\nEach: each")
        if not result: return
        result = result.strip()
        outdir = filedialog.askdirectory(title="Output Folder")
        if not outdir: return
        base = os.path.splitext(os.path.basename(self.original_path or "out"))[0]

        if result.lower() == "each":
            ranges = [(i, i+1) for i in range(total)]
        elif result.isdigit():
            n = int(result)
            ranges = [(s, min(s+n, total)) for s in range(0, total, n)]
        else:
            ranges = []
            try:
                for part in result.split(","):
                    part = part.strip()
                    if "-" in part:
                        a, b = part.split("-", 1)
                        ranges.append((int(a)-1, int(b)))
                    else:
                        p = int(part)-1; ranges.append((p, p+1))
            except: messagebox.showerror("Error", "Invalid format."); return

        count = 0
        for idx, (s, e) in enumerate(ranges):
            w = PdfWriter()
            for i in range(s, min(e, total)): w.add_page(self.reader.pages[i])
            if w.pages:
                with open(os.path.join(outdir, f"{base}_part{idx+1}.pdf"), "wb") as f: w.write(f)
                count += 1
        messagebox.showinfo("Split", f"Created {count} file(s) in:\n{outdir}")

    def split_size(self):
        if not self._need_pdf(): return
        result = simpledialog.askstring("Split by Size", "Max size: 1MB, 500KB")
        if not result: return
        result = result.strip().upper()
        try:
            if result.endswith("MB"): max_b = float(result[:-2]) * 1024 * 1024
            elif result.endswith("KB"): max_b = float(result[:-2]) * 1024
            else: max_b = float(result)
        except: messagebox.showerror("Error", "Invalid size."); return
        outdir = filedialog.askdirectory(title="Output Folder")
        if not outdir: return
        base = os.path.splitext(os.path.basename(self.original_path or "out"))[0]
        total = len(self.reader.pages); part = 0; i = 0
        while i < total:
            pages = [i]; i += 1
            while i < total:
                tw = PdfWriter()
                for pi in pages + [i]: tw.add_page(self.reader.pages[pi])
                buf = io.BytesIO(); tw.write(buf)
                if buf.tell() > max_b: break
                pages.append(i); i += 1
            part += 1; w = PdfWriter()
            for pi in pages: w.add_page(self.reader.pages[pi])
            with open(os.path.join(outdir, f"{base}_part{part}.pdf"), "wb") as f: w.write(f)
        messagebox.showinfo("Split", f"Created {part} file(s) in:\n{outdir}")

    # ── Internal ──

    def _apply(self, writer):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        writer.write(tmp); tmp.close()
        self.reader = PdfReader(tmp.name)
        self.loaded_path = tmp.name
        self.modified = True
        name = os.path.basename(self.original_path) if self.original_path else "PDF"
        self.file_label.config(text=f"\u25C9  {name}  ({len(self.reader.pages)} pages)  [modified]", fg=ACCENT)
        self._refresh_list()

    def _load(self, path):
        self.reader = PdfReader(path)
        self.loaded_path = path
        self.original_path = path
        self.modified = False
        name = os.path.basename(path)
        self.file_label.config(text=f"\u25CF  {name}  ({len(self.reader.pages)} pages)", fg=FG)
        self.root.title(f"PDF Editor Lite - {name}")
        self._refresh_list()


def main():
    root = tk.Tk()
    PDFEditorLite(root)
    root.mainloop()


if __name__ == "__main__":
    main()
