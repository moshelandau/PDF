#!/usr/bin/env python3
"""PDF Editor - Modern visual PDF editor."""

import io
import os
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog


def _check_and_install_deps():
    required = {"PyPDF2": "PyPDF2", "fitz": "PyMuPDF", "PIL": "Pillow"}
    missing = []
    for module, package in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    if missing:
        print(f"Installing: {', '.join(missing)}...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install"] + missing,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception as e:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Setup Error",
                f"Failed to install:\n{', '.join(missing)}\n\npip install {' '.join(missing)}\n\n{e}")
            sys.exit(1)


_check_and_install_deps()

from PyPDF2 import PdfReader, PdfWriter

try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

# ── Theme ──────────────────────────────────────────────────
DEFAULT_THUMB_W = 180
DEFAULT_THUMB_H = 240
MIN_THUMB = 100
MAX_THUMB = 400

# Colors - Modern dark blue theme
BG_MAIN = "#0f1923"
BG_TOOLBAR = "#162232"
BG_SIDEBAR = "#132030"
BG_CARD = "#1a2d42"
BG_CARD_HOVER = "#1f3550"
BG_CARD_SEL = "#0d4f8b"
BG_STATUS = "#0c1620"
BG_CANVAS = "#0f1923"
ACCENT = "#2196F3"
ACCENT_LIGHT = "#64B5F6"
ACCENT_DIM = "#1565C0"
TEXT_PRIMARY = "#e0e6ed"
TEXT_SECONDARY = "#8899aa"
TEXT_DIM = "#556677"
BORDER = "#1e3a54"
BORDER_SEL = "#2196F3"
DANGER = "#e74c3c"
SUCCESS = "#27ae60"
WHITE = "#ffffff"


class PageCard:
    def __init__(self, canvas, index, thumb_image, page_info, x, y, w, h, on_click, on_dblclick):
        self.canvas = canvas
        self.index = index
        self.selected = False
        self.x, self.y = x, y
        self.card_w, self.card_h = w, h
        self.on_click = on_click
        self.on_dblclick = on_dblclick
        self.thumb_image = thumb_image
        self.page_info = page_info
        self.items = []
        self.draw()

    def draw(self):
        for item in self.items:
            self.canvas.delete(item)
        self.items.clear()

        x, y, w, h = self.x, self.y, self.card_w, self.card_h
        sel = self.selected
        bg = BG_CARD_SEL if sel else BG_CARD
        border = BORDER_SEL if sel else BORDER
        bw = 2 if sel else 1

        # Soft shadow
        s = self.canvas.create_rectangle(x+2, y+2, x+w+2, y+h+2, fill="#080e15", outline="")
        self.items.append(s)

        # Card
        r = self.canvas.create_rectangle(x, y, x+w, y+h, fill=bg, outline=border, width=bw)
        self.items.append(r)

        # Selection indicator bar
        if sel:
            bar = self.canvas.create_rectangle(x, y, x+3, y+h, fill=ACCENT, outline="")
            self.items.append(bar)

        # Thumbnail area
        thumb_h = h - 40
        if self.thumb_image:
            img = self.canvas.create_image(x + w//2, y + 5 + thumb_h//2, image=self.thumb_image)
            self.items.append(img)
        else:
            # Stylish placeholder
            ph = self.canvas.create_rectangle(x+8, y+5, x+w-8, y+5+thumb_h, fill="#0d1f30", outline="#1e3a54")
            self.items.append(ph)
            # Page icon
            icon_y = y + 5 + thumb_h//2 - 15
            pg = self.canvas.create_text(x+w//2, icon_y, text="\u25A4",
                                          fill=TEXT_DIM, font=("Segoe UI", 24))
            self.items.append(pg)
            num = self.canvas.create_text(x+w//2, icon_y + 30, text=str(self.index + 1),
                                           fill=TEXT_SECONDARY, font=("Segoe UI", 12, "bold"))
            self.items.append(num)

        # Page label
        lbl_color = WHITE if sel else TEXT_PRIMARY
        lbl = self.canvas.create_text(x + w//2, y + 5 + thumb_h + 8,
                                       text=f"Page {self.index + 1}",
                                       fill=lbl_color, font=("Segoe UI", 9, "bold"), anchor="n")
        self.items.append(lbl)

        # Info text
        info_color = ACCENT_LIGHT if sel else TEXT_DIM
        inf = self.canvas.create_text(x + w//2, y + 5 + thumb_h + 23,
                                       text=self.page_info,
                                       fill=info_color, font=("Segoe UI", 7), anchor="n")
        self.items.append(inf)

        for item in self.items:
            self.canvas.tag_bind(item, "<Button-1>", lambda e: self.on_click(self, e))
            self.canvas.tag_bind(item, "<Double-Button-1>", lambda e: self.on_dblclick(self, e))

    def set_selected(self, val):
        if self.selected != val:
            self.selected = val
            self.draw()


class PageViewer(tk.Toplevel):
    def __init__(self, parent, reader, page_index, pdf_path):
        super().__init__(parent)
        self.reader = reader
        self.page_index = page_index
        self.pdf_path = pdf_path
        self.zoom = 1.0
        self.photo = None
        total = len(reader.pages)
        self.title(f"Page {page_index + 1} of {total}")
        self.geometry("950x780")
        self.configure(bg=BG_MAIN)

        # Toolbar
        top = tk.Frame(self, bg=BG_TOOLBAR, padx=10, pady=8)
        top.pack(fill=tk.X)

        self._btn(top, "\u25C0  Prev", self._prev).pack(side=tk.LEFT, padx=(0,4))
        self._btn(top, "Next  \u25B6", self._next).pack(side=tk.LEFT, padx=4)

        self.page_label = tk.Label(top, text=f"Page {page_index+1} / {total}",
                                    bg=BG_TOOLBAR, fg=WHITE, font=("Segoe UI", 12, "bold"))
        self.page_label.pack(side=tk.LEFT, padx=15)

        self._btn(top, "\u2212", self._zoom_out).pack(side=tk.LEFT, padx=2)
        self.zoom_label = tk.Label(top, text="100%", bg=BG_TOOLBAR, fg=ACCENT_LIGHT,
                                    font=("Segoe UI", 10, "bold"), width=5)
        self.zoom_label.pack(side=tk.LEFT, padx=4)
        self._btn(top, "+", self._zoom_in).pack(side=tk.LEFT, padx=2)
        self._btn(top, "Fit Width", self._fit_width).pack(side=tk.LEFT, padx=(10,2))

        # Canvas
        cf = tk.Frame(self, bg=BG_MAIN)
        cf.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.canvas = tk.Canvas(cf, bg="#141e2b", highlightthickness=0)
        vs = ttk.Scrollbar(cf, orient=tk.VERTICAL, command=self.canvas.yview)
        hs = ttk.Scrollbar(cf, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        hs.pack(side=tk.BOTTOM, fill=tk.X)
        vs.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas.bind("<MouseWheel>", self._on_scroll)
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-3, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(3, "units"))
        self.bind("<Left>", lambda e: self._prev())
        self.bind("<Right>", lambda e: self._next())
        self.bind("<Escape>", lambda e: self.destroy())
        self.after(50, self._render)

    def _btn(self, parent, text, cmd):
        b = tk.Button(parent, text=text, command=cmd, bg=BG_CARD, fg=TEXT_PRIMARY,
                      activebackground=ACCENT_DIM, activeforeground=WHITE, relief="flat",
                      font=("Segoe UI", 9), padx=10, pady=3, cursor="hand2",
                      highlightthickness=0, bd=0)
        return b

    def _on_scroll(self, e):
        if e.state & 0x4:
            self._zoom_in() if e.delta > 0 else self._zoom_out()
        else:
            self.canvas.yview_scroll(-1*(e.delta//120), "units")

    def _prev(self):
        if self.page_index > 0:
            self.page_index -= 1; self._render()

    def _next(self):
        if self.page_index < len(self.reader.pages)-1:
            self.page_index += 1; self._render()

    def _zoom_in(self):
        self.zoom = min(5.0, self.zoom + 0.25); self._render()

    def _zoom_out(self):
        self.zoom = max(0.25, self.zoom - 0.25); self._render()

    def _fit_width(self):
        if not HAS_FITZ or not self.pdf_path: return
        try:
            doc = fitz.open(self.pdf_path)
            pw = doc[self.page_index].rect.width; doc.close()
            cw = self.canvas.winfo_width() - 40
            if cw > 50 and pw > 0: self.zoom = cw / pw; self._render()
        except Exception: pass

    def _render(self):
        total = len(self.reader.pages)
        self.title(f"Page {self.page_index+1} of {total}")
        self.page_label.config(text=f"Page {self.page_index+1} / {total}")
        self.zoom_label.config(text=f"{int(self.zoom*100)}%")
        self.canvas.delete("all")

        if HAS_FITZ and HAS_PIL and self.pdf_path:
            try:
                doc = fitz.open(self.pdf_path)
                page = doc[self.page_index]
                mat = fitz.Matrix(self.zoom*1.5, self.zoom*1.5)
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                doc.close()
                self.photo = ImageTk.PhotoImage(img)
                self.canvas.create_image(20, 20, anchor="nw", image=self.photo)
                self.canvas.configure(scrollregion=(0, 0, pix.width+40, pix.height+40))
                return
            except Exception: pass

        p = self.reader.pages[self.page_index]; box = p.mediabox
        self.canvas.create_text(self.canvas.winfo_width()//2, 80,
            text=f"Page {self.page_index+1}\n{float(box.width):.0f} x {float(box.height):.0f} pt",
            fill=TEXT_SECONDARY, font=("Segoe UI", 14), justify="center")


class PDFEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Editor")
        self.root.geometry("1150x780")
        self.root.minsize(850, 600)
        self.root.configure(bg=BG_MAIN)

        self.loaded_pdf_path = None
        self.original_path = None
        self.reader = None
        self.page_cards = []
        self.thumb_images = []
        self.modified = False
        self.thumb_w = DEFAULT_THUMB_W
        self.thumb_h = DEFAULT_THUMB_H

        self._build_ui()

    def _make_btn(self, parent, text, cmd, style="normal"):
        if style == "accent":
            bg, fg, abg = ACCENT, WHITE, ACCENT_DIM
        elif style == "danger":
            bg, fg, abg = "#3a1520", "#ff6b6b", DANGER
        else:
            bg, fg, abg = BG_CARD, TEXT_PRIMARY, BG_CARD_HOVER

        def on_cmd(btn_ref=None, normal_bg=bg, hover_bg=abg):
            cmd()
            # After a dialog closes, <Leave> may never fire, leaving the
            # button stuck in its hover (light) state.  Reset based on
            # whether the pointer is still over the button.
            if btn_ref:
                btn_ref.after(50, lambda: self._reset_btn_hover(btn_ref, normal_bg, hover_bg))

        b = tk.Button(parent, text=text, command=lambda: on_cmd(b, bg, abg),
                      bg=bg, fg=fg,
                      activebackground=abg, activeforeground=WHITE,
                      relief="flat", font=("Segoe UI", 9), padx=12, pady=5,
                      cursor="hand2", highlightthickness=0, bd=0)
        # Hover effect
        b.bind("<Enter>", lambda e: b.config(bg=abg))
        b.bind("<Leave>", lambda e: b.config(bg=bg))
        return b

    @staticmethod
    def _reset_btn_hover(btn, normal_bg, hover_bg):
        """Reset button bg after a dialog may have stolen the <Leave> event."""
        try:
            mx, my = btn.winfo_pointerxy()
            bx, by = btn.winfo_rootx(), btn.winfo_rooty()
            if bx <= mx <= bx + btn.winfo_width() and by <= my <= by + btn.winfo_height():
                btn.config(bg=hover_bg)
            else:
                btn.config(bg=normal_bg)
        except tk.TclError:
            pass

    def _make_sep(self, parent):
        sep = tk.Frame(parent, width=1, bg=BORDER)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=6)

    def _build_ui(self):
        # ── Title bar ──
        title_bar = tk.Frame(self.root, bg=BG_TOOLBAR, height=40)
        title_bar.pack(fill=tk.X)
        title_bar.pack_propagate(False)

        tk.Label(title_bar, text="\u25A4  PDF Editor", bg=BG_TOOLBAR, fg=ACCENT_LIGHT,
                 font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, padx=15, pady=8)

        self.title_info = tk.Label(title_bar, text="", bg=BG_TOOLBAR, fg=TEXT_SECONDARY,
                                    font=("Segoe UI", 10))
        self.title_info.pack(side=tk.LEFT, padx=5)

        # ── Main toolbar ──
        toolbar = tk.Frame(self.root, bg=BG_TOOLBAR, padx=10, pady=6)
        toolbar.pack(fill=tk.X)

        # File group
        tk.Label(toolbar, text="FILE", bg=BG_TOOLBAR, fg=TEXT_DIM,
                 font=("Segoe UI", 7, "bold")).pack(side=tk.LEFT, padx=(0,6))
        self._make_btn(toolbar, "\U0001F4C2 Open", self.open_pdf, "accent").pack(side=tk.LEFT, padx=2)
        self._make_btn(toolbar, "\U0001F4BE Save", self.save).pack(side=tk.LEFT, padx=2)
        self._make_btn(toolbar, "Save As", self.save_as).pack(side=tk.LEFT, padx=2)

        self._make_sep(toolbar)

        # Rotate group
        tk.Label(toolbar, text="ROTATE", bg=BG_TOOLBAR, fg=TEXT_DIM,
                 font=("Segoe UI", 7, "bold")).pack(side=tk.LEFT, padx=(0,6))
        self._make_btn(toolbar, "\u21BB CW", lambda: self.rotate_pages(90)).pack(side=tk.LEFT, padx=2)
        self._make_btn(toolbar, "\u21BA CCW", lambda: self.rotate_pages(270)).pack(side=tk.LEFT, padx=2)
        self._make_btn(toolbar, "180\u00B0", lambda: self.rotate_pages(180)).pack(side=tk.LEFT, padx=2)
        self._make_btn(toolbar, "\u2B6F Auto", self.auto_rotate).pack(side=tk.LEFT, padx=2)

        self._make_sep(toolbar)

        # Edit group
        tk.Label(toolbar, text="EDIT", bg=BG_TOOLBAR, fg=TEXT_DIM,
                 font=("Segoe UI", 7, "bold")).pack(side=tk.LEFT, padx=(0,6))
        self._make_btn(toolbar, "\u2716 Delete", self.delete_pages, "danger").pack(side=tk.LEFT, padx=2)
        self._make_btn(toolbar, "\u2795 Merge", self.merge_pdfs).pack(side=tk.LEFT, padx=2)
        self._make_btn(toolbar, "\u2702 Split", self.split_by_pages).pack(side=tk.LEFT, padx=2)
        self._make_btn(toolbar, "\u2696 Split Size", self.split_by_size).pack(side=tk.LEFT, padx=2)

        self._make_sep(toolbar)

        # Zoom slider
        tk.Label(toolbar, text="SIZE", bg=BG_TOOLBAR, fg=TEXT_DIM,
                 font=("Segoe UI", 7, "bold")).pack(side=tk.LEFT, padx=(0,4))
        self.size_var = tk.IntVar(value=DEFAULT_THUMB_W)
        scale = tk.Scale(toolbar, from_=MIN_THUMB, to=MAX_THUMB, variable=self.size_var,
                         orient=tk.HORIZONTAL, length=100, command=self._on_size_change,
                         bg=BG_TOOLBAR, fg=TEXT_SECONDARY, troughcolor=BG_CARD,
                         highlightthickness=0, sliderrelief="flat", bd=0, showvalue=False,
                         activebackground=ACCENT)
        scale.pack(side=tk.LEFT, padx=2)
        self.size_label = tk.Label(toolbar, text=f"{DEFAULT_THUMB_W}", bg=BG_TOOLBAR,
                                    fg=ACCENT_LIGHT, font=("Segoe UI", 8, "bold"), width=3)
        self.size_label.pack(side=tk.LEFT)

        # ── Info bar ──
        info_bar = tk.Frame(self.root, bg=BG_SIDEBAR, padx=12, pady=5)
        info_bar.pack(fill=tk.X)

        self.file_label = tk.Label(info_bar, text="\u25CB  No file loaded",
                                    bg=BG_SIDEBAR, fg=TEXT_SECONDARY,
                                    font=("Segoe UI", 10))
        self.file_label.pack(side=tk.LEFT)

        self.selection_label = tk.Label(info_bar, text="", bg=BG_SIDEBAR, fg=ACCENT_LIGHT,
                                         font=("Segoe UI", 9))
        self.selection_label.pack(side=tk.RIGHT)

        # ── Page grid ──
        grid_frame = tk.Frame(self.root, bg=BG_CANVAS)
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self.canvas = tk.Canvas(grid_frame, bg=BG_CANVAS, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(grid_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas.bind("<Configure>", lambda e: self._render_page_grid())
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1*(e.delta//120), "units"))
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-3, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(3, "units"))

        # ── Status bar ──
        status = tk.Frame(self.root, bg=BG_STATUS, height=28)
        status.pack(fill=tk.X, side=tk.BOTTOM)
        status.pack_propagate(False)

        self.status_label = tk.Label(status, text="  Ready  |  Click = select  |  Ctrl+Click = multi  |  Ctrl+A = all  |  Double-click = expand  |  Del = remove",
                                      bg=BG_STATUS, fg=TEXT_DIM, font=("Segoe UI", 8), anchor="w")
        self.status_label.pack(side=tk.LEFT, padx=8)

        self.status_right = tk.Label(status, text="", bg=BG_STATUS, fg=TEXT_DIM,
                                      font=("Segoe UI", 8), anchor="e")
        self.status_right.pack(side=tk.RIGHT, padx=8)

        # ── Keyboard shortcuts ──
        self.root.bind("<Control-o>", lambda e: self.open_pdf())
        self.root.bind("<Control-a>", lambda e: self._select_all())
        self.root.bind("<Delete>", lambda e: self.delete_pages())
        self.root.bind("<Control-s>", lambda e: self.save())
        self.root.bind("<Control-S>", lambda e: self.save_as())

    def _on_size_change(self, val):
        new_w = int(float(val))
        new_h = int(new_w * DEFAULT_THUMB_H / DEFAULT_THUMB_W)
        if new_w != self.thumb_w:
            self.thumb_w = new_w
            self.thumb_h = new_h
            self.size_label.config(text=f"{new_w}")
            self.thumb_images = []
            self._render_page_grid()
            if hasattr(self, '_size_after_id'):
                self.root.after_cancel(self._size_after_id)
            self._size_after_id = self.root.after(300, self._start_thumb_gen)

    def _start_thumb_gen(self):
        if HAS_FITZ and self.loaded_pdf_path:
            threading.Thread(target=self._generate_thumbs, daemon=True).start()

    # ── Thumbnails ──

    def _render_thumb_from_doc(self, doc, page_index):
        try:
            page = doc[page_index]
            scale = min(self.thumb_w / page.rect.width, self.thumb_h / page.rect.height)
            mat = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            canvas_img = Image.new("RGB", (self.thumb_w, self.thumb_h), "#0d1f30")
            x_off = (self.thumb_w - img.width) // 2
            y_off = (self.thumb_h - img.height) // 2
            canvas_img.paste(img, (x_off, y_off))

            draw = ImageDraw.Draw(canvas_img)
            draw.rectangle([0, 0, self.thumb_w-1, self.thumb_h-1], outline="#1e3a54")
            return ImageTk.PhotoImage(canvas_img)
        except Exception:
            return None

    def _generate_thumbs(self):
        if not self.reader or not self.loaded_pdf_path: return
        path = self.loaded_pdf_path
        total = len(self.reader.pages)
        tw, th = self.thumb_w, self.thumb_h

        while len(self.thumb_images) < total:
            self.thumb_images.append(None)

        try:
            doc = fitz.open(path)
        except Exception:
            return

        for i in range(total):
            if self.loaded_pdf_path != path or self.thumb_w != tw or self.thumb_h != th:
                doc.close(); return
            thumb = self._render_thumb_from_doc(doc, i)
            if thumb:
                self.thumb_images[i] = thumb
            if (i+1) % 5 == 0 or i == total-1:
                self.root.after(0, self._render_page_grid)
                self.root.after(0, lambda i=i: self.status_right.config(
                    text=f"Loading thumbnails... {i+1}/{total}"))

        doc.close()
        self.root.after(0, lambda: self.status_right.config(text=f"{total} pages loaded"))

    def _make_placeholder(self, index, w, h, rotation):
        if not HAS_PIL: return None
        img = Image.new("RGB", (self.thumb_w, self.thumb_h), "#0d1f30")
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, self.thumb_w-1, self.thumb_h-1], outline="#1e3a54")
        try:
            font = ImageFont.truetype("arial.ttf", max(14, self.thumb_w // 8))
            small = ImageFont.truetype("arial.ttf", max(9, self.thumb_w // 16))
        except (OSError, IOError):
            font = ImageFont.load_default(); small = font
        text = str(index + 1)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th2 = bbox[2]-bbox[0], bbox[3]-bbox[1]
        draw.text(((self.thumb_w-tw)//2, self.thumb_h//2 - th2), text, fill="#4a6a8a", font=font)
        info = f"{w:.0f}x{h:.0f}"
        bbox2 = draw.textbbox((0, 0), info, font=small)
        iw = bbox2[2]-bbox2[0]
        draw.text(((self.thumb_w-iw)//2, self.thumb_h//2 + 8), info, fill="#2a4a6a", font=small)
        return ImageTk.PhotoImage(img)

    # ── Grid ──

    def _render_page_grid(self):
        self.canvas.delete("all")
        old_sel = {c.index for c in self.page_cards if c.selected}
        self.page_cards.clear()

        if not self.reader:
            cw = max(self.canvas.winfo_width(), 800)
            ch = max(self.canvas.winfo_height(), 400)
            # Welcome screen
            self.canvas.create_text(cw//2, ch//2 - 40, text="\u25A4",
                                     fill=TEXT_DIM, font=("Segoe UI", 48))
            self.canvas.create_text(cw//2, ch//2 + 20, text="Open a PDF to get started",
                                     fill=TEXT_SECONDARY, font=("Segoe UI", 16))
            self.canvas.create_text(cw//2, ch//2 + 50, text="Ctrl+O  or  click Open",
                                     fill=TEXT_DIM, font=("Segoe UI", 11))
            return

        canvas_w = max(self.canvas.winfo_width(), 800)
        pad = 8
        card_w = self.thumb_w + pad*2
        card_h = self.thumb_h + 46
        gap = 16
        cols = max(1, (canvas_w - gap) // (card_w + gap))
        total = len(self.reader.pages)
        rows = (total + cols - 1) // cols
        grid_w = cols * (card_w + gap) - gap
        x_start = max(gap, (canvas_w - grid_w) // 2)

        for i, page in enumerate(self.reader.pages):
            row, col = i // cols, i % cols
            x = x_start + col * (card_w + gap)
            y = gap + row * (card_h + gap)

            box = page.mediabox
            w, h = float(box.width), float(box.height)
            rotation = page.get("/Rotate", 0)
            info = f"{w:.0f} x {h:.0f}"
            if rotation: info += f"  \u21BB{rotation}\u00B0"

            thumb = None
            if i < len(self.thumb_images) and self.thumb_images[i]:
                thumb = self.thumb_images[i]
            elif HAS_PIL:
                thumb = self._make_placeholder(i, w, h, rotation)
                while len(self.thumb_images) <= i:
                    self.thumb_images.append(None)
                self.thumb_images[i] = thumb

            card = PageCard(self.canvas, i, thumb, info, x, y, card_w, card_h,
                            self._on_card_click, self._on_card_dblclick)
            if i in old_sel:
                card.set_selected(True)
            self.page_cards.append(card)

        total_h = gap + rows * (card_h + gap) + gap
        self.canvas.configure(scrollregion=(0, 0, canvas_w, total_h))
        self._update_selection_label()

    def _on_card_click(self, card, event):
        if event.state & 0x4:
            card.set_selected(not card.selected)
        else:
            for c in self.page_cards: c.set_selected(False)
            card.set_selected(True)
        self._update_selection_label()

    def _on_card_dblclick(self, card, event):
        if self.reader and self.loaded_pdf_path:
            PageViewer(self.root, self.reader, card.index, self.loaded_pdf_path)

    def _select_all(self):
        for c in self.page_cards: c.set_selected(True)
        self._update_selection_label()

    def _update_selection_label(self):
        sel = [c for c in self.page_cards if c.selected]
        total = len(self.page_cards)
        if sel:
            nums = ", ".join(str(c.index+1) for c in sel[:8])
            if len(sel) > 8: nums += f"  +{len(sel)-8} more"
            self.selection_label.config(text=f"\u2713 {len(sel)}/{total} selected  [{nums}]")
        else:
            self.selection_label.config(text=f"{total} pages" if total else "")

    def _get_selected_indices(self):
        sel = tuple(c.index for c in self.page_cards if c.selected)
        if not sel:
            messagebox.showinfo("Select Pages", "Click on pages to select them first.\n\nCtrl+Click for multiple.")
        return sel

    def _require_pdf(self):
        if not self.reader:
            messagebox.showinfo("No PDF", "Open a PDF file first.")
            return False
        return True

    # ── File ops ──

    def open_pdf(self):
        path = filedialog.askopenfilename(title="Open PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if not path: return
        try:
            self.reader = PdfReader(path)
            self.loaded_pdf_path = path
            self.original_path = path
            self.modified = False
            self.thumb_images = []
            name = os.path.basename(path)
            pages = len(self.reader.pages)
            self.file_label.config(text=f"\u25CF  {name}  ({pages} pages)", fg=TEXT_PRIMARY)
            self.title_info.config(text=f"  {name}")
            self.root.title(f"PDF Editor - {name}")
            self.status_right.config(text=f"Loading {pages} pages...")
            self._render_page_grid()
            if HAS_FITZ:
                threading.Thread(target=self._generate_thumbs, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open PDF:\n{e}")

    def save(self):
        if not self._require_pdf(): return
        if not self.original_path: self.save_as(); return
        if not self.modified:
            messagebox.showinfo("Save", "No changes to save."); return
        if not messagebox.askyesno("Save", f"Overwrite?\n\n{self.original_path}"): return
        writer = PdfWriter()
        for page in self.reader.pages: writer.add_page(page)
        with open(self.original_path, "wb") as f: writer.write(f)
        self._load_path(self.original_path)
        self.status_label.config(text=f"  Saved to {os.path.basename(self.original_path)}")

    def save_as(self):
        if not self._require_pdf(): return
        name = os.path.basename(self.original_path) if self.original_path else "output.pdf"
        out = filedialog.asksaveasfilename(title="Save PDF As", defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")], initialfile=name)
        if not out: return
        writer = PdfWriter()
        for page in self.reader.pages: writer.add_page(page)
        with open(out, "wb") as f: writer.write(f)
        messagebox.showinfo("Saved", f"Saved to:\n{out}")
        self._load_path(out)

    # ── Page ops ──

    def rotate_pages(self, degrees):
        if not self._require_pdf(): return
        indices = self._get_selected_indices()
        if not indices: return
        writer = PdfWriter()
        for i, page in enumerate(self.reader.pages):
            if i in indices: page = page.rotate(degrees)
            writer.add_page(page)
        self._apply_writer(writer)
        self.status_label.config(text=f"  Rotated {len(indices)} page(s) {degrees}\u00B0")

    def auto_rotate(self):
        if not self._require_pdf(): return
        URL = "https://github.com/tesseract-ocr/tesseract/releases/download/5.5.0/tesseract-ocr-w64-setup-5.5.0.20241111.exe"
        ocr_ok = HAS_OCR and HAS_FITZ and HAS_PIL
        if ocr_ok:
            try: pytesseract.get_tesseract_version()
            except: ocr_ok = False

        if ocr_ok:
            ch = messagebox.askyesnocancel("Auto-Rotate",
                "Yes = OCR (smart, reads text)\nNo = Simple (landscape to portrait)\nCancel = abort")
            if ch is None: return
            if ch: self._auto_rotate_ocr()
            else: self._auto_rotate_simple()
        else:
            ch = messagebox.askyesnocancel("Auto-Rotate",
                f"OCR not available.\n\nInstall Tesseract for smart rotate:\n{URL}\n\n"
                "Yes = Download Tesseract\nNo = Simple rotate\nCancel = abort")
            if ch is None: return
            if ch: import webbrowser; webbrowser.open(URL)
            else: self._auto_rotate_simple()

    def _auto_rotate_simple(self):
        writer = PdfWriter(); count = 0
        for page in self.reader.pages:
            box = page.mediabox
            if float(box.width) > float(box.height): page = page.rotate(90); count += 1
            writer.add_page(page)
        self._apply_writer(writer)
        self.status_label.config(text=f"  Auto-rotated {count} landscape page(s)")

    def _auto_rotate_ocr(self):
        if not self.loaded_pdf_path: return
        writer = PdfWriter(); count = 0
        doc = fitz.open(self.loaded_pdf_path)
        for i, page in enumerate(self.reader.pages):
            rot = self._detect_ocr(doc, i)
            if rot != 0: page = page.rotate(rot); count += 1
            writer.add_page(page)
        doc.close()
        self._apply_writer(writer)
        self.status_label.config(text=f"  OCR rotated {count} page(s)")

    def _detect_ocr(self, doc, idx):
        page = doc[idx]
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        best_rot, best_conf = 0, -1
        for angle in [0, 90, 180, 270]:
            rotated = img.rotate(-angle, expand=True) if angle else img
            try:
                osd = pytesseract.image_to_osd(rotated, output_type=pytesseract.Output.DICT)
                conf = osd.get("orientation_conf", 0)
                if conf > best_conf and osd.get("rotate", 0) == 0:
                    best_conf = conf; best_rot = angle
            except:
                try:
                    score = len(pytesseract.image_to_string(rotated).strip())
                    if score > best_conf: best_conf = score; best_rot = angle
                except: pass
        return best_rot

    def delete_pages(self):
        if not self._require_pdf(): return
        indices = self._get_selected_indices()
        if not indices: return
        nums = ", ".join(str(i+1) for i in indices)
        if not messagebox.askyesno("Delete", f"Delete page(s) {nums}?"): return
        writer = PdfWriter()
        for i, page in enumerate(self.reader.pages):
            if i not in indices: writer.add_page(page)
        if not writer.pages:
            messagebox.showwarning("Warning", "Cannot delete all pages."); return
        self._apply_writer(writer)
        self.status_label.config(text=f"  Deleted {len(indices)} page(s)")

    def merge_pdfs(self):
        paths = filedialog.askopenfilenames(
            title="Select PDFs to merge  (Ctrl+Click for multiple)", filetypes=[("PDF", "*.pdf")])
        if not paths: return
        if len(paths) < 2 and not self.reader:
            messagebox.showinfo("Merge", "Select 2+ files. Hold Ctrl to pick multiple."); return
        writer = PdfWriter(); info = []
        if self.reader:
            for p in self.reader.pages: writer.add_page(p)
            info.append(f"  Current: {os.path.basename(self.original_path or '?')} ({len(self.reader.pages)}p)")
        for path in paths:
            try:
                r = PdfReader(path)
                for p in r.pages: writer.add_page(p)
                info.append(f"  + {os.path.basename(path)} ({len(r.pages)}p)")
            except Exception as e:
                messagebox.showerror("Error", f"Failed: {os.path.basename(path)}\n{e}"); return
        if not messagebox.askyesno("Merge", "\n".join(info) + f"\n\nTotal: {len(writer.pages)} pages"): return
        out = filedialog.asksaveasfilename(title="Save Merged", defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")], initialfile="merged.pdf")
        if not out: return
        with open(out, "wb") as f: writer.write(f)
        self._load_path(out)
        self.status_label.config(text=f"  Merged {len(writer.pages)} pages")

    def split_by_pages(self):
        if not self._require_pdf(): return
        total = len(self.reader.pages)
        result = simpledialog.askstring("Split",
            f"Total: {total} pages\n\nRanges: 1-3, 4-6, 7-10\nEvery N: 3\nEach page: each",
            parent=self.root)
        if not result: return
        result = result.strip()
        outdir = filedialog.askdirectory(title="Output Directory")
        if not outdir: return
        base = os.path.splitext(os.path.basename(self.original_path or "output"))[0]

        if result.lower() == "each":
            ranges = [(i, i+1) for i in range(total)]
        elif result.isdigit():
            n = int(result)
            if n < 1: return
            ranges = [(s, min(s+n, total)) for s in range(0, total, n)]
        else:
            ranges = []
            try:
                for part in result.split(","):
                    part = part.strip()
                    if "-" in part:
                        a, b = part.split("-", 1)
                        ranges.append((int(a.strip())-1, int(b.strip())))
                    else:
                        p = int(part.strip())-1; ranges.append((p, p+1))
            except ValueError:
                messagebox.showerror("Error", "Invalid format."); return

        saved = []
        for idx, (start, end) in enumerate(ranges):
            w = PdfWriter()
            for i in range(start, min(end, total)): w.add_page(self.reader.pages[i])
            if w.pages:
                fn = f"{base}_part{idx+1}.pdf"; fp = os.path.join(outdir, fn)
                with open(fp, "wb") as f: w.write(f)
                kb = os.path.getsize(fp) / 1024
                saved.append(f"  {fn}  ({len(w.pages)}p, {kb:.0f}KB)")
        messagebox.showinfo("Split", f"Created {len(saved)} file(s):\n{outdir}\n\n" + "\n".join(saved))
        self.status_label.config(text=f"  Split into {len(saved)} files")

    def split_by_size(self):
        if not self._require_pdf(): return
        result = simpledialog.askstring("Split by Size", "Max size: 1MB, 500KB, 2.5MB", parent=self.root)
        if not result: return
        result = result.strip().upper()
        try:
            if result.endswith("MB"): max_b = float(result[:-2]) * 1024 * 1024
            elif result.endswith("KB"): max_b = float(result[:-2]) * 1024
            else: max_b = float(result)
        except ValueError:
            messagebox.showerror("Error", "Invalid size."); return
        outdir = filedialog.askdirectory(title="Output Directory")
        if not outdir: return
        base = os.path.splitext(os.path.basename(self.original_path or "output"))[0]
        total = len(self.reader.pages); part = 0; saved = []; i = 0
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
            fn = f"{base}_part{part}.pdf"; fp = os.path.join(outdir, fn)
            with open(fp, "wb") as f: w.write(f)
            kb = os.path.getsize(fp) / 1024
            saved.append(f"  {fn}  ({len(w.pages)}p, {kb:.0f}KB)")
        messagebox.showinfo("Split", f"Created {part} file(s):\n{outdir}\n\n" + "\n".join(saved))

    # ── Internal ──

    def _apply_writer(self, writer):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        writer.write(tmp); tmp.close()
        self.reader = PdfReader(tmp.name)
        self.loaded_pdf_path = tmp.name
        self.modified = True
        self.thumb_images = []
        name = os.path.basename(self.original_path) if self.original_path else "PDF"
        self.file_label.config(text=f"\u25C9  {name}  ({len(self.reader.pages)} pages)  [modified]", fg=ACCENT_LIGHT)
        self._render_page_grid()
        if HAS_FITZ:
            threading.Thread(target=self._generate_thumbs, daemon=True).start()

    def _load_path(self, path):
        self.reader = PdfReader(path)
        self.loaded_pdf_path = path
        self.original_path = path
        self.modified = False
        self.thumb_images = []
        name = os.path.basename(path)
        self.file_label.config(text=f"\u25CF  {name}  ({len(self.reader.pages)} pages)", fg=TEXT_PRIMARY)
        self.title_info.config(text=f"  {name}")
        self.root.title(f"PDF Editor - {name}")
        self._render_page_grid()
        if HAS_FITZ:
            threading.Thread(target=self._generate_thumbs, daemon=True).start()


def main():
    root = tk.Tk()
    PDFEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
