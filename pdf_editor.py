#!/usr/bin/env python3
"""PDF Editor - Visual page editor with real page previews."""

import io
import os
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from PyPDF2 import PdfReader, PdfWriter

try:
    import fitz  # PyMuPDF
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

DEFAULT_THUMB_W = 180
DEFAULT_THUMB_H = 240
MIN_THUMB = 100
MAX_THUMB = 400

BG_COLOR = "#1e1e1e"
CARD_BG = "#2d2d2d"
CARD_SELECTED = "#1a4a7a"
TEXT_COLOR = "#cccccc"
TEXT_SELECTED = "#ffffff"
ACCENT = "#4a9eff"
TOOLBAR_BG = "#252526"
BORDER_COLOR = "#444444"
BORDER_SELECTED = "#4a9eff"


class PageCard:
    """One page thumbnail card in the grid."""

    def __init__(self, canvas, index, thumb_image, page_info, x, y, w, h, on_click, on_dblclick):
        self.canvas = canvas
        self.index = index
        self.selected = False
        self.x = x
        self.y = y
        self.card_w = w
        self.card_h = h
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

        x, y = self.x, self.y
        bg = CARD_SELECTED if self.selected else CARD_BG
        border = BORDER_SELECTED if self.selected else BORDER_COLOR
        text_col = TEXT_SELECTED if self.selected else TEXT_COLOR
        bw = 2 if self.selected else 1

        # Shadow
        shadow = self.canvas.create_rectangle(
            x + 3, y + 3, x + self.card_w + 3, y + self.card_h + 3,
            fill="#111111", outline=""
        )
        self.items.append(shadow)

        # Card bg
        rect = self.canvas.create_rectangle(
            x, y, x + self.card_w, y + self.card_h,
            fill=bg, outline=border, width=bw
        )
        self.items.append(rect)

        # Thumbnail
        thumb_area_h = self.card_h - 36
        if self.thumb_image:
            img = self.canvas.create_image(
                x + self.card_w // 2, y + 6 + thumb_area_h // 2,
                image=self.thumb_image
            )
            self.items.append(img)
        else:
            ph = self.canvas.create_rectangle(
                x + 6, y + 6, x + self.card_w - 6, y + 6 + thumb_area_h,
                fill="#3a3a3a", outline="#505050"
            )
            self.items.append(ph)
            txt = self.canvas.create_text(
                x + self.card_w // 2, y + 6 + thumb_area_h // 2,
                text=f"Page {self.index + 1}", fill="#888888", font=("Segoe UI", 11)
            )
            self.items.append(txt)

        # Page number
        label = self.canvas.create_text(
            x + self.card_w // 2, y + 6 + thumb_area_h + 6,
            text=f"Page {self.index + 1}", fill=text_col, font=("Segoe UI", 9, "bold"), anchor="n"
        )
        self.items.append(label)

        # Info
        info = self.canvas.create_text(
            x + self.card_w // 2, y + 6 + thumb_area_h + 20,
            text=self.page_info, fill="#888888" if not self.selected else "#aaaaaa",
            font=("Segoe UI", 7), anchor="n"
        )
        self.items.append(info)

        for item in self.items:
            self.canvas.tag_bind(item, "<Button-1>", lambda e: self.on_click(self, e))
            self.canvas.tag_bind(item, "<Double-Button-1>", lambda e: self.on_dblclick(self, e))

    def set_selected(self, selected):
        if self.selected != selected:
            self.selected = selected
            self.draw()


class PageViewer(tk.Toplevel):
    """Full-size page viewer window."""

    def __init__(self, parent, reader, page_index, pdf_path):
        super().__init__(parent)
        self.reader = reader
        self.page_index = page_index
        self.pdf_path = pdf_path
        self.zoom = 1.0
        self.photo = None

        total = len(reader.pages)
        self.title(f"Page {page_index + 1} of {total}")
        self.geometry("900x750")
        self.configure(bg=BG_COLOR)

        # Top bar
        top = ttk.Frame(self, style="Dark.TFrame")
        top.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(top, text="< Prev", command=self._prev, style="Tool.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="Next >", command=self._next, style="Tool.TButton").pack(side=tk.LEFT, padx=2)

        self.page_label = ttk.Label(top, text=f"  Page {page_index + 1} / {total}  ",
                                     style="Dark.TLabel", font=("Segoe UI", 11, "bold"))
        self.page_label.pack(side=tk.LEFT, padx=10)

        ttk.Button(top, text="Zoom -", command=self._zoom_out, style="Tool.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="Zoom +", command=self._zoom_in, style="Tool.TButton").pack(side=tk.LEFT, padx=2)

        self.zoom_label = ttk.Label(top, text="100%", style="Dark.TLabel")
        self.zoom_label.pack(side=tk.LEFT, padx=5)

        ttk.Button(top, text="Fit Width", command=self._fit_width, style="Tool.TButton").pack(side=tk.LEFT, padx=2)

        # Canvas for page
        canvas_frame = ttk.Frame(self, style="Dark.TFrame")
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        self.canvas = tk.Canvas(canvas_frame, bg="#333333", highlightthickness=0)
        self.v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)

        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas.bind("<MouseWheel>", self._on_scroll)
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-3, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(3, "units"))

        self.bind("<Left>", lambda e: self._prev())
        self.bind("<Right>", lambda e: self._next())
        self.bind("<plus>", lambda e: self._zoom_in())
        self.bind("<minus>", lambda e: self._zoom_out())
        self.bind("<Escape>", lambda e: self.destroy())

        self.after(50, self._render_page)

    def _on_scroll(self, event):
        if event.state & 0x4:  # Ctrl held
            if event.delta > 0:
                self._zoom_in()
            else:
                self._zoom_out()
        else:
            self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def _prev(self):
        if self.page_index > 0:
            self.page_index -= 1
            self._render_page()

    def _next(self):
        if self.page_index < len(self.reader.pages) - 1:
            self.page_index += 1
            self._render_page()

    def _zoom_in(self):
        self.zoom = min(5.0, self.zoom + 0.25)
        self._render_page()

    def _zoom_out(self):
        self.zoom = max(0.25, self.zoom - 0.25)
        self._render_page()

    def _fit_width(self):
        if not HAS_FITZ or not self.pdf_path:
            return
        try:
            doc = fitz.open(self.pdf_path)
            page = doc[self.page_index]
            pw = page.rect.width
            doc.close()
            canvas_w = self.canvas.winfo_width() - 40
            if canvas_w > 50 and pw > 0:
                self.zoom = canvas_w / pw
                self._render_page()
        except Exception:
            pass

    def _render_page(self):
        total = len(self.reader.pages)
        self.title(f"Page {self.page_index + 1} of {total}")
        self.page_label.config(text=f"  Page {self.page_index + 1} / {total}  ")
        self.zoom_label.config(text=f"{int(self.zoom * 100)}%")
        self.canvas.delete("all")

        if HAS_FITZ and HAS_PIL and self.pdf_path:
            try:
                doc = fitz.open(self.pdf_path)
                page = doc[self.page_index]
                mat = fitz.Matrix(self.zoom * 1.5, self.zoom * 1.5)
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                doc.close()

                self.photo = ImageTk.PhotoImage(img)
                self.canvas.create_image(20, 20, anchor="nw", image=self.photo)
                self.canvas.configure(scrollregion=(0, 0, pix.width + 40, pix.height + 40))
                return
            except Exception:
                pass

        # Fallback: text info
        p = self.reader.pages[self.page_index]
        box = p.mediabox
        self.canvas.create_text(
            self.canvas.winfo_width() // 2, 80,
            text=f"Page {self.page_index + 1}\n{float(box.width):.0f} x {float(box.height):.0f} pt\n\n"
                 f"Install PyMuPDF for page rendering:\n  pip install PyMuPDF",
            fill=TEXT_COLOR, font=("Segoe UI", 14), justify="center"
        )


class PDFEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Editor")
        self.root.geometry("1100x750")
        self.root.minsize(800, 550)
        self.root.configure(bg=BG_COLOR)

        self.loaded_pdf_path = None
        self.original_path = None
        self.reader = None
        self.page_cards = []
        self.thumb_images = []
        self.modified = False
        self.thumb_w = DEFAULT_THUMB_W
        self.thumb_h = DEFAULT_THUMB_H

        self._setup_style()
        self._build_ui()

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.TFrame", background=BG_COLOR)
        style.configure("Toolbar.TFrame", background=TOOLBAR_BG)
        style.configure("Dark.TLabel", background=BG_COLOR, foreground=TEXT_COLOR, font=("Segoe UI", 10))
        style.configure("Toolbar.TLabel", background=TOOLBAR_BG, foreground=TEXT_COLOR, font=("Segoe UI", 10))
        style.configure("Accent.TButton", font=("Segoe UI", 9, "bold"), padding=(12, 5))
        style.configure("Tool.TButton", font=("Segoe UI", 9), padding=(8, 4))
        style.configure("Dark.TButton", font=("Segoe UI", 9), padding=(10, 5))
        style.configure("Dark.TScale", background=TOOLBAR_BG, troughcolor="#3a3a3a")

    def _build_ui(self):
        # Top toolbar
        toolbar = ttk.Frame(self.root, style="Toolbar.TFrame")
        toolbar.pack(fill=tk.X, padx=0, pady=0)

        inner = ttk.Frame(toolbar, style="Toolbar.TFrame")
        inner.pack(fill=tk.X, padx=8, pady=6)

        ttk.Button(inner, text="Open", command=self.open_pdf, style="Accent.TButton").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(inner, text="Save", command=self.save, style="Dark.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(inner, text="Save As", command=self.save_as, style="Dark.TButton").pack(side=tk.LEFT, padx=2)

        self._sep(inner)

        ttk.Button(inner, text="Rotate CW", command=lambda: self.rotate_pages(90), style="Tool.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(inner, text="Rotate CCW", command=lambda: self.rotate_pages(270), style="Tool.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(inner, text="Rotate 180", command=lambda: self.rotate_pages(180), style="Tool.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(inner, text="Auto-Rotate", command=self.auto_rotate, style="Tool.TButton").pack(side=tk.LEFT, padx=2)

        self._sep(inner)

        ttk.Button(inner, text="Delete", command=self.delete_pages, style="Tool.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(inner, text="Merge", command=self.merge_pdfs, style="Tool.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(inner, text="Split Pages", command=self.split_by_pages, style="Tool.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(inner, text="Split Size", command=self.split_by_size, style="Tool.TButton").pack(side=tk.LEFT, padx=2)

        # Size slider on the right
        self._sep(inner)
        ttk.Label(inner, text="Size:", style="Toolbar.TLabel").pack(side=tk.LEFT, padx=(4, 2))
        self.size_var = tk.IntVar(value=DEFAULT_THUMB_W)
        size_scale = ttk.Scale(inner, from_=MIN_THUMB, to=MAX_THUMB, variable=self.size_var,
                                orient=tk.HORIZONTAL, length=120, command=self._on_size_change,
                                style="Dark.TScale")
        size_scale.pack(side=tk.LEFT, padx=2)
        self.size_label = ttk.Label(inner, text=f"{DEFAULT_THUMB_W}px", style="Toolbar.TLabel",
                                     font=("Segoe UI", 8))
        self.size_label.pack(side=tk.LEFT, padx=2)

        # Info bar
        info_bar = ttk.Frame(self.root, style="Dark.TFrame")
        info_bar.pack(fill=tk.X, padx=10, pady=(6, 0))

        self.file_label = ttk.Label(info_bar, text="No file loaded  —  Open a PDF to start",
                                     style="Dark.TLabel", font=("Segoe UI", 10))
        self.file_label.pack(side=tk.LEFT)

        self.selection_label = ttk.Label(info_bar, text="", style="Dark.TLabel", font=("Segoe UI", 9))
        self.selection_label.pack(side=tk.RIGHT)

        # Tips
        tip_bar = ttk.Frame(self.root, style="Dark.TFrame")
        tip_bar.pack(fill=tk.X, padx=10)
        ttk.Label(tip_bar,
                   text="Click = select  |  Ctrl+Click = multi-select  |  Ctrl+A = all  |  Double-click = expand page  |  Delete = remove",
                   style="Dark.TLabel", font=("Segoe UI", 8), foreground="#666666").pack(side=tk.LEFT)

        # Page grid canvas
        grid_frame = ttk.Frame(self.root, style="Dark.TFrame")
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))

        self.canvas = tk.Canvas(grid_frame, bg=BG_COLOR, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(grid_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas.bind("<Configure>", lambda e: self._render_page_grid())
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-3, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(3, "units"))

        # Keyboard shortcuts
        self.root.bind("<Control-o>", lambda e: self.open_pdf())
        self.root.bind("<Control-a>", lambda e: self._select_all())
        self.root.bind("<Delete>", lambda e: self.delete_pages())
        self.root.bind("<Control-s>", lambda e: self.save())
        self.root.bind("<Control-S>", lambda e: self.save_as())

    def _sep(self, parent):
        sep = ttk.Frame(parent, width=2, style="Dark.TFrame")
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=2)

    def _on_size_change(self, val):
        new_w = int(float(val))
        new_h = int(new_w * DEFAULT_THUMB_H / DEFAULT_THUMB_W)
        if new_w != self.thumb_w:
            self.thumb_w = new_w
            self.thumb_h = new_h
            self.size_label.config(text=f"{new_w}px")
            self.thumb_images = []
            self._render_page_grid()
            if HAS_FITZ and self.loaded_pdf_path:
                threading.Thread(target=self._generate_thumbs, daemon=True).start()

    # --- Thumbnail generation ---

    def _render_thumb_fitz(self, page_index):
        """Render a single page thumbnail using PyMuPDF."""
        if not HAS_FITZ or not HAS_PIL or not self.loaded_pdf_path:
            return None
        try:
            doc = fitz.open(self.loaded_pdf_path)
            page = doc[page_index]
            # Scale to fit thumb size
            scale = min(self.thumb_w / page.rect.width, self.thumb_h / page.rect.height)
            mat = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            doc.close()

            # Center on canvas
            canvas_img = Image.new("RGB", (self.thumb_w, self.thumb_h), "#3a3a3a")
            x_off = (self.thumb_w - img.width) // 2
            y_off = (self.thumb_h - img.height) // 2
            canvas_img.paste(img, (x_off, y_off))

            # Add thin border
            draw = ImageDraw.Draw(canvas_img)
            draw.rectangle([0, 0, self.thumb_w - 1, self.thumb_h - 1], outline="#555555")

            return ImageTk.PhotoImage(canvas_img)
        except Exception:
            return None

    def _generate_thumbs(self):
        """Generate all thumbnails in background thread."""
        if not self.reader or not self.loaded_pdf_path:
            return
        total = len(self.reader.pages)
        new_thumbs = [None] * total
        for i in range(total):
            thumb = self._render_thumb_fitz(i)
            if thumb:
                new_thumbs[i] = thumb
        self.thumb_images = new_thumbs
        self.root.after(0, self._render_page_grid)

    def _make_placeholder(self, index, w, h, rotation):
        """Simple placeholder when PyMuPDF not available."""
        if not HAS_PIL:
            return None
        img = Image.new("RGB", (self.thumb_w, self.thumb_h), "#3a3a3a")
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, self.thumb_w - 1, self.thumb_h - 1], outline="#555555")
        try:
            font = ImageFont.truetype("arial.ttf", max(14, self.thumb_w // 8))
            small = ImageFont.truetype("arial.ttf", max(9, self.thumb_w // 16))
        except (OSError, IOError):
            font = ImageFont.load_default()
            small = font
        text = str(index + 1)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((self.thumb_w - tw) // 2, self.thumb_h // 2 - th), text, fill="#aaaaaa", font=font)
        info = f"{w:.0f}x{h:.0f}"
        bbox2 = draw.textbbox((0, 0), info, font=small)
        iw = bbox2[2] - bbox2[0]
        draw.text(((self.thumb_w - iw) // 2, self.thumb_h // 2 + 8), info, fill="#777777", font=small)
        return ImageTk.PhotoImage(img)

    # --- Grid rendering ---

    def _render_page_grid(self):
        self.canvas.delete("all")
        old_selected = {c.index for c in self.page_cards if c.selected}
        self.page_cards.clear()

        if not self.reader:
            cw = self.canvas.winfo_width()
            if cw < 10:
                cw = 800
            self.canvas.create_text(
                cw // 2, 120,
                text="Open a PDF file to see pages here\n\nCtrl+O or click Open",
                fill="#555555", font=("Segoe UI", 16), justify="center"
            )
            return

        canvas_w = self.canvas.winfo_width()
        if canvas_w < 10:
            canvas_w = 800

        pad = 8
        card_w = self.thumb_w + pad * 2
        card_h = self.thumb_h + 42
        gap = 14
        cols = max(1, (canvas_w - gap) // (card_w + gap))
        total = len(self.reader.pages)
        rows = (total + cols - 1) // cols

        total_grid_w = cols * (card_w + gap) - gap
        x_start = max(gap, (canvas_w - total_grid_w) // 2)

        for i, page in enumerate(self.reader.pages):
            row = i // cols
            col = i % cols
            x = x_start + col * (card_w + gap)
            y = gap + row * (card_h + gap)

            box = page.mediabox
            w, h = float(box.width), float(box.height)
            rotation = page.get("/Rotate", 0)
            info = f"{w:.0f} x {h:.0f} pt"
            if rotation:
                info += f"  rot {rotation}"

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
            if i in old_selected:
                card.set_selected(True)
            self.page_cards.append(card)

        total_h = gap + rows * (card_h + gap) + gap
        self.canvas.configure(scrollregion=(0, 0, canvas_w, total_h))
        self._update_selection_label()

    def _on_card_click(self, card, event):
        ctrl = event.state & 0x4
        if ctrl:
            card.set_selected(not card.selected)
        else:
            for c in self.page_cards:
                c.set_selected(False)
            card.set_selected(True)
        self._update_selection_label()

    def _on_card_dblclick(self, card, event):
        """Open full-size page viewer."""
        if not self.reader or not self.loaded_pdf_path:
            return
        PageViewer(self.root, self.reader, card.index, self.loaded_pdf_path)

    def _select_all(self):
        for c in self.page_cards:
            c.set_selected(True)
        self._update_selection_label()

    def _update_selection_label(self):
        selected = [c for c in self.page_cards if c.selected]
        total = len(self.page_cards)
        if selected:
            nums = ", ".join(str(c.index + 1) for c in selected[:8])
            if len(selected) > 8:
                nums += f" ... (+{len(selected) - 8})"
            self.selection_label.config(text=f"Selected {len(selected)}/{total}  [{nums}]")
        else:
            self.selection_label.config(text=f"{total} pages" if total else "")

    def _get_selected_indices(self):
        sel = tuple(c.index for c in self.page_cards if c.selected)
        if not sel:
            messagebox.showinfo("Info", "No pages selected.\nClick on page thumbnails to select.")
        return sel

    def _require_pdf(self):
        if not self.reader:
            messagebox.showinfo("Info", "Open a PDF file first.")
            return False
        return True

    # --- File ops ---

    def open_pdf(self):
        path = filedialog.askopenfilename(
            title="Open PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            self.reader = PdfReader(path)
            self.loaded_pdf_path = path
            self.original_path = path
            self.modified = False
            self.thumb_images = []
            self.file_label.config(text=f"{os.path.basename(path)}  ({len(self.reader.pages)} pages)")
            self.root.title(f"PDF Editor — {os.path.basename(path)}")
            self._render_page_grid()
            if HAS_FITZ:
                threading.Thread(target=self._generate_thumbs, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open PDF:\n{e}")

    def save(self):
        """Save to original file (overwrite)."""
        if not self._require_pdf():
            return
        if not self.original_path:
            self.save_as()
            return
        if not self.modified:
            messagebox.showinfo("Save", "No changes to save.")
            return
        if not messagebox.askyesno("Confirm Save",
                                    f"Overwrite the original file?\n\n{self.original_path}"):
            return
        writer = PdfWriter()
        for page in self.reader.pages:
            writer.add_page(page)
        with open(self.original_path, "wb") as f:
            writer.write(f)
        self._load_path(self.original_path)
        messagebox.showinfo("Saved", f"Saved to:\n{self.original_path}")

    def save_as(self):
        """Save to a new file."""
        if not self._require_pdf():
            return
        default_name = os.path.basename(self.original_path) if self.original_path else "output.pdf"
        out = filedialog.asksaveasfilename(
            title="Save PDF As", defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")], initialfile=default_name
        )
        if not out:
            return
        writer = PdfWriter()
        for page in self.reader.pages:
            writer.add_page(page)
        with open(out, "wb") as f:
            writer.write(f)
        messagebox.showinfo("Saved", f"PDF saved to:\n{out}")
        self._load_path(out)

    # --- Page ops ---

    def rotate_pages(self, degrees):
        if not self._require_pdf():
            return
        indices = self._get_selected_indices()
        if not indices:
            return
        writer = PdfWriter()
        for i, page in enumerate(self.reader.pages):
            if i in indices:
                page = page.rotate(degrees)
            writer.add_page(page)
        self._apply_writer(writer)

    def auto_rotate(self):
        if not self._require_pdf():
            return

        TESSERACT_URL = "https://github.com/tesseract-ocr/tesseract/releases/download/5.5.0/tesseract-ocr-w64-setup-5.5.0.20241111.exe"

        ocr_available = HAS_OCR and HAS_FITZ and HAS_PIL
        if ocr_available:
            # Check if tesseract binary is actually installed
            try:
                pytesseract.get_tesseract_version()
            except Exception:
                ocr_available = False

        if ocr_available:
            choice = messagebox.askyesnocancel(
                "Auto-Rotate",
                "Use OCR to detect correct page orientation?\n\n"
                "Yes = OCR (smart, reads text direction)\n"
                "No = Simple (rotate landscape to portrait)\n"
                "Cancel = abort"
            )
            if choice is None:
                return
            if choice:
                self._auto_rotate_ocr()
            else:
                self._auto_rotate_simple()
        else:
            choice = messagebox.askyesnocancel(
                "Auto-Rotate",
                "OCR smart rotate is not available.\n\n"
                "To enable it, install Tesseract OCR:\n"
                f"{TESSERACT_URL}\n\n"
                "Yes = Open download link\n"
                "No = Use simple rotate (landscape to portrait)\n"
                "Cancel = abort"
            )
            if choice is None:
                return
            if choice:
                import webbrowser
                webbrowser.open(TESSERACT_URL)
            else:
                self._auto_rotate_simple()

    def _auto_rotate_simple(self):
        writer = PdfWriter()
        count = 0
        for page in self.reader.pages:
            box = page.mediabox
            if float(box.width) > float(box.height):
                page = page.rotate(90)
                count += 1
            writer.add_page(page)
        self._apply_writer(writer)
        messagebox.showinfo("Auto-Rotate", f"Rotated {count} landscape page(s) to portrait.")

    def _auto_rotate_ocr(self):
        """Use OCR to detect page orientation and rotate accordingly."""
        if not self.loaded_pdf_path:
            return

        writer = PdfWriter()
        count = 0
        doc = fitz.open(self.loaded_pdf_path)

        for i, page in enumerate(self.reader.pages):
            best_rotation = self._detect_orientation_ocr(doc, i)
            if best_rotation != 0:
                page = page.rotate(best_rotation)
                count += 1
            writer.add_page(page)

        doc.close()
        self._apply_writer(writer)
        messagebox.showinfo("OCR Auto-Rotate", f"Rotated {count} page(s) based on text orientation.")

    def _detect_orientation_ocr(self, doc, page_index):
        """Try each rotation (0, 90, 180, 270) and pick the one with most detected text."""
        page = doc[page_index]
        # Render at moderate resolution for OCR
        base_mat = fitz.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=base_mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        best_rotation = 0
        best_confidence = -1

        for angle in [0, 90, 180, 270]:
            rotated = img.rotate(-angle, expand=True) if angle != 0 else img
            try:
                osd = pytesseract.image_to_osd(rotated, output_type=pytesseract.Output.DICT)
                confidence = osd.get("orientation_conf", 0)
                detected_angle = osd.get("rotate", 0)
                # If OSD says rotate 0 with high confidence, this orientation is correct
                if confidence > best_confidence and detected_angle == 0:
                    best_confidence = confidence
                    best_rotation = angle
            except Exception:
                # Fallback: count text characters
                try:
                    text = pytesseract.image_to_string(rotated)
                    score = len(text.strip())
                    if score > best_confidence:
                        best_confidence = score
                        best_rotation = angle
                except Exception:
                    pass

        return best_rotation

    def delete_pages(self):
        if not self._require_pdf():
            return
        indices = self._get_selected_indices()
        if not indices:
            return
        nums = ", ".join(str(i + 1) for i in indices)
        if not messagebox.askyesno("Confirm Delete", f"Delete page(s) {nums}?"):
            return
        writer = PdfWriter()
        for i, page in enumerate(self.reader.pages):
            if i not in indices:
                writer.add_page(page)
        if len(writer.pages) == 0:
            messagebox.showwarning("Warning", "Cannot delete all pages.")
            return
        self._apply_writer(writer)

    # --- Merge ---

    def merge_pdfs(self):
        paths = filedialog.askopenfilenames(
            title="Select PDF files to merge  (Ctrl+Click or Shift+Click for multiple)",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not paths:
            return
        if len(paths) < 2 and not self.reader:
            messagebox.showinfo("Merge",
                                "Select at least 2 files to merge.\n\n"
                                "Hold Ctrl and click to pick multiple files,\n"
                                "or hold Shift to select a range.")
            return
        writer = PdfWriter()
        info_lines = []
        if self.reader:
            for page in self.reader.pages:
                writer.add_page(page)
            info_lines.append(f"  Current: {os.path.basename(self.original_path or '?')} ({len(self.reader.pages)} pages)")
        for path in paths:
            try:
                r = PdfReader(path)
                for page in r.pages:
                    writer.add_page(page)
                info_lines.append(f"  + {os.path.basename(path)} ({len(r.pages)} pages)")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read {os.path.basename(path)}:\n{e}")
                return
        msg = "Merging:\n" + "\n".join(info_lines) + f"\n\nTotal: {len(writer.pages)} pages"
        if not messagebox.askyesno("Confirm Merge", msg):
            return
        out = filedialog.asksaveasfilename(
            title="Save Merged PDF", defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")], initialfile="merged.pdf"
        )
        if not out:
            return
        with open(out, "wb") as f:
            writer.write(f)
        messagebox.showinfo("Merge", f"Merged {len(writer.pages)} pages saved!")
        self._load_path(out)

    # --- Split ---

    def split_by_pages(self):
        if not self._require_pdf():
            return
        total = len(self.reader.pages)
        result = simpledialog.askstring(
            "Split by Pages",
            f"Total pages: {total}\n\n"
            "Enter page ranges:  1-3, 4-6, 7-10\n"
            "Or a number to split every N pages:  3\n"
            "Or 'each' for one page per file.",
            parent=self.root
        )
        if not result:
            return
        result = result.strip()
        outdir = filedialog.askdirectory(title="Select Output Directory")
        if not outdir:
            return
        base = os.path.splitext(os.path.basename(self.original_path or "output"))[0]

        if result.lower() == "each":
            ranges = [(i, i + 1) for i in range(total)]
        elif result.isdigit():
            n = int(result)
            if n < 1:
                return
            ranges = [(s, min(s + n, total)) for s in range(0, total, n)]
        else:
            ranges = []
            try:
                for part in result.split(","):
                    part = part.strip()
                    if "-" in part:
                        a, b = part.split("-", 1)
                        ranges.append((int(a.strip()) - 1, int(b.strip())))
                    else:
                        p = int(part.strip()) - 1
                        ranges.append((p, p + 1))
            except ValueError:
                messagebox.showerror("Error", "Invalid format.")
                return

        saved_files = []
        for idx, (start, end) in enumerate(ranges):
            writer = PdfWriter()
            for i in range(start, min(end, total)):
                writer.add_page(self.reader.pages[i])
            if len(writer.pages) > 0:
                filename = f"{base}_part{idx + 1}.pdf"
                filepath = os.path.join(outdir, filename)
                with open(filepath, "wb") as f:
                    writer.write(f)
                size_kb = os.path.getsize(filepath) / 1024
                saved_files.append(f"  {filename}  ({len(writer.pages)} pages, {size_kb:.0f} KB)")

        file_list = "\n".join(saved_files)
        messagebox.showinfo("Split Complete",
                            f"Created {len(saved_files)} file(s) in:\n{outdir}\n\n{file_list}")

    def split_by_size(self):
        if not self._require_pdf():
            return
        result = simpledialog.askstring(
            "Split by Size", "Max size per part:\n  e.g. 1MB, 500KB, 2.5MB",
            parent=self.root
        )
        if not result:
            return
        result = result.strip().upper()
        try:
            if result.endswith("MB"):
                max_bytes = float(result[:-2]) * 1024 * 1024
            elif result.endswith("KB"):
                max_bytes = float(result[:-2]) * 1024
            else:
                max_bytes = float(result)
        except ValueError:
            messagebox.showerror("Error", "Invalid size. Use e.g. 1MB, 500KB.")
            return
        outdir = filedialog.askdirectory(title="Select Output Directory")
        if not outdir:
            return
        base = os.path.splitext(os.path.basename(self.original_path or "output"))[0]
        total = len(self.reader.pages)
        part_num = 0
        saved_files = []
        i = 0
        while i < total:
            pages_in_part = [i]
            i += 1
            while i < total:
                test_writer = PdfWriter()
                for pi in pages_in_part + [i]:
                    test_writer.add_page(self.reader.pages[pi])
                buf = io.BytesIO()
                test_writer.write(buf)
                if buf.tell() > max_bytes:
                    break
                pages_in_part.append(i)
                i += 1
            part_num += 1
            writer = PdfWriter()
            for pi in pages_in_part:
                writer.add_page(self.reader.pages[pi])
            filename = f"{base}_part{part_num}.pdf"
            filepath = os.path.join(outdir, filename)
            with open(filepath, "wb") as f:
                writer.write(f)
            size_kb = os.path.getsize(filepath) / 1024
            saved_files.append(f"  {filename}  ({len(writer.pages)} pages, {size_kb:.0f} KB)")

        file_list = "\n".join(saved_files)
        messagebox.showinfo("Split by Size",
                            f"Created {part_num} file(s) in:\n{outdir}\n\n{file_list}")

    # --- Internal ---

    def _apply_writer(self, writer):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        writer.write(tmp)
        tmp.close()
        self.reader = PdfReader(tmp.name)
        self.loaded_pdf_path = tmp.name
        self.modified = True
        self.thumb_images = []
        name = os.path.basename(self.original_path) if self.original_path else "PDF"
        self.file_label.config(text=f"{name}  ({len(self.reader.pages)} pages)  [modified]")
        self._render_page_grid()
        if HAS_FITZ:
            threading.Thread(target=self._generate_thumbs, daemon=True).start()

    def _load_path(self, path):
        self.reader = PdfReader(path)
        self.loaded_pdf_path = path
        self.original_path = path
        self.modified = False
        self.thumb_images = []
        self.file_label.config(text=f"{os.path.basename(path)}  ({len(self.reader.pages)} pages)")
        self.root.title(f"PDF Editor — {os.path.basename(path)}")
        self._render_page_grid()
        if HAS_FITZ:
            threading.Thread(target=self._generate_thumbs, daemon=True).start()


def main():
    root = tk.Tk()
    PDFEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
