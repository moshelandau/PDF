#!/usr/bin/env python3
"""PDF Editor - Visual page editor with thumbnails."""

import io
import os
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from PyPDF2 import PdfReader, PdfWriter

try:
    from pdf2image import convert_from_path
    HAS_PDF2IMAGE = True
except ImportError:
    HAS_PDF2IMAGE = False

try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

THUMB_WIDTH = 150
THUMB_HEIGHT = 200
BG_COLOR = "#2b2b2b"
CARD_BG = "#3c3f41"
CARD_SELECTED = "#2d5ca6"
CARD_HOVER = "#4a4d50"
TEXT_COLOR = "#bbbbbb"
TEXT_SELECTED = "#ffffff"
ACCENT = "#4a9eff"


class PageCard:
    """Represents one page thumbnail in the grid."""

    def __init__(self, canvas, index, thumb_image, page_info, x, y, on_click):
        self.canvas = canvas
        self.index = index
        self.selected = False
        self.x = x
        self.y = y
        self.on_click = on_click
        self.thumb_image = thumb_image
        self.page_info = page_info
        self.items = []
        self.draw(x, y)

    def draw(self, x, y):
        for item in self.items:
            self.canvas.delete(item)
        self.items.clear()

        bg = CARD_SELECTED if self.selected else CARD_BG
        text_col = TEXT_SELECTED if self.selected else TEXT_COLOR
        pad = 6
        card_w = THUMB_WIDTH + pad * 2
        card_h = THUMB_HEIGHT + 40

        # Card background
        rect = self.canvas.create_rectangle(
            x, y, x + card_w, y + card_h,
            fill=bg, outline=ACCENT if self.selected else "#555555", width=2 if self.selected else 1
        )
        self.items.append(rect)

        # Thumbnail image
        if self.thumb_image:
            img = self.canvas.create_image(x + card_w // 2, y + pad + THUMB_HEIGHT // 2, image=self.thumb_image)
            self.items.append(img)
        else:
            # Placeholder
            placeholder = self.canvas.create_rectangle(
                x + pad, y + pad, x + pad + THUMB_WIDTH, y + pad + THUMB_HEIGHT,
                fill="#555555", outline="#666666"
            )
            self.items.append(placeholder)
            txt = self.canvas.create_text(
                x + card_w // 2, y + pad + THUMB_HEIGHT // 2,
                text=f"Page\n{self.index + 1}", fill="#999999", font=("Segoe UI", 12)
            )
            self.items.append(txt)

        # Page label
        label = self.canvas.create_text(
            x + card_w // 2, y + pad + THUMB_HEIGHT + 8,
            text=f"Page {self.index + 1}", fill=text_col, font=("Segoe UI", 10, "bold"),
            anchor="n"
        )
        self.items.append(label)

        # Page info
        info = self.canvas.create_text(
            x + card_w // 2, y + pad + THUMB_HEIGHT + 24,
            text=self.page_info, fill=text_col, font=("Segoe UI", 8),
            anchor="n"
        )
        self.items.append(info)

        # Bind clicks
        for item in self.items:
            self.canvas.tag_bind(item, "<Button-1>", lambda e: self.on_click(self, e))

    def set_selected(self, selected):
        if self.selected != selected:
            self.selected = selected
            self.draw(self.x, self.y)


class PDFEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Editor")
        self.root.geometry("1050x700")
        self.root.minsize(800, 550)
        self.root.configure(bg=BG_COLOR)

        self.loaded_pdf_path = None
        self.original_path = None
        self.reader = None
        self.page_cards = []
        self.thumb_images = []
        self.modified = False

        self._setup_style()
        self._build_ui()

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.TFrame", background=BG_COLOR)
        style.configure("Dark.TLabelframe", background=BG_COLOR, foreground=TEXT_COLOR)
        style.configure("Dark.TLabelframe.Label", background=BG_COLOR, foreground=TEXT_COLOR,
                         font=("Segoe UI", 10))
        style.configure("Dark.TLabel", background=BG_COLOR, foreground=TEXT_COLOR,
                         font=("Segoe UI", 10))
        style.configure("Accent.TButton", font=("Segoe UI", 9), padding=(10, 5))
        style.configure("Tool.TButton", font=("Segoe UI", 9), padding=(8, 4))
        style.configure("Dark.TButton", font=("Segoe UI", 9), padding=(10, 5))

    def _build_ui(self):
        # Top toolbar
        toolbar = ttk.Frame(self.root, style="Dark.TFrame")
        toolbar.pack(fill=tk.X, padx=8, pady=(8, 4))

        ttk.Button(toolbar, text="Open PDF", command=self.open_pdf, style="Accent.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Save As", command=self.save_as, style="Dark.TButton").pack(side=tk.LEFT, padx=2)

        sep1 = ttk.Separator(toolbar, orient=tk.VERTICAL)
        sep1.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)

        ttk.Button(toolbar, text="Rotate 90 CW", command=lambda: self.rotate_pages(90), style="Tool.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Rotate 90 CCW", command=lambda: self.rotate_pages(270), style="Tool.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Rotate 180", command=lambda: self.rotate_pages(180), style="Tool.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Auto-Rotate", command=self.auto_rotate, style="Tool.TButton").pack(side=tk.LEFT, padx=2)

        sep2 = ttk.Separator(toolbar, orient=tk.VERTICAL)
        sep2.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)

        ttk.Button(toolbar, text="Delete Pages", command=self.delete_pages, style="Tool.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Merge PDFs", command=self.merge_pdfs, style="Tool.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Split Pages", command=self.split_by_pages, style="Tool.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Split Size", command=self.split_by_size, style="Tool.TButton").pack(side=tk.LEFT, padx=2)

        # File info bar
        info_bar = ttk.Frame(self.root, style="Dark.TFrame")
        info_bar.pack(fill=tk.X, padx=8, pady=2)

        self.file_label = ttk.Label(info_bar, text="No file loaded  -  Open a PDF to get started",
                                     style="Dark.TLabel")
        self.file_label.pack(side=tk.LEFT)

        self.selection_label = ttk.Label(info_bar, text="", style="Dark.TLabel")
        self.selection_label.pack(side=tk.RIGHT)

        # Tip bar
        tip_bar = ttk.Frame(self.root, style="Dark.TFrame")
        tip_bar.pack(fill=tk.X, padx=8)
        self.tip_label = ttk.Label(tip_bar,
                                    text="Tip: Click to select a page | Ctrl+Click for multiple | Ctrl+A to select all",
                                    style="Dark.TLabel", font=("Segoe UI", 8))
        self.tip_label.pack(side=tk.LEFT)

        # Page grid area (canvas with scrollbar)
        grid_frame = ttk.Frame(self.root, style="Dark.TFrame")
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))

        self.canvas = tk.Canvas(grid_frame, bg=BG_COLOR, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(grid_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas.bind("<Configure>", lambda e: self._render_page_grid())
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        # Linux scroll
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-3, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(3, "units"))

        # Keyboard shortcuts
        self.root.bind("<Control-o>", lambda e: self.open_pdf())
        self.root.bind("<Control-a>", lambda e: self._select_all())
        self.root.bind("<Delete>", lambda e: self.delete_pages())
        self.root.bind("<Control-s>", lambda e: self.save_as())

    def _generate_placeholder_thumb(self, index, width, height, rotation):
        """Generate a placeholder thumbnail with page info."""
        if not HAS_PIL:
            return None
        img = Image.new("RGB", (THUMB_WIDTH, THUMB_HEIGHT), "#444444")
        draw = ImageDraw.Draw(img)
        # Border
        draw.rectangle([0, 0, THUMB_WIDTH - 1, THUMB_HEIGHT - 1], outline="#666666")
        # Page number
        try:
            font = ImageFont.truetype("arial.ttf", 20)
            small_font = ImageFont.truetype("arial.ttf", 11)
        except (OSError, IOError):
            font = ImageFont.load_default()
            small_font = font
        text = str(index + 1)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(((THUMB_WIDTH - tw) // 2, THUMB_HEIGHT // 2 - th - 5), text,
                  fill="#cccccc", font=font)
        # Size info
        info = f"{width:.0f}x{height:.0f}"
        bbox2 = draw.textbbox((0, 0), info, font=small_font)
        iw = bbox2[2] - bbox2[0]
        draw.text(((THUMB_WIDTH - iw) // 2, THUMB_HEIGHT // 2 + 10), info,
                  fill="#999999", font=small_font)
        if rotation:
            rot_text = f"Rot: {rotation}"
            bbox3 = draw.textbbox((0, 0), rot_text, font=small_font)
            rw = bbox3[2] - bbox3[0]
            draw.text(((THUMB_WIDTH - rw) // 2, THUMB_HEIGHT // 2 + 26), rot_text,
                      fill="#999999", font=small_font)
        return ImageTk.PhotoImage(img)

    def _generate_real_thumbs(self):
        """Try to generate real page thumbnails using pdf2image."""
        if not HAS_PDF2IMAGE or not HAS_PIL or not self.loaded_pdf_path:
            return
        try:
            images = convert_from_path(
                self.loaded_pdf_path,
                size=(THUMB_WIDTH * 2, THUMB_HEIGHT * 2),
                fmt="png"
            )
            self.thumb_images = []
            for img in images:
                img.thumbnail((THUMB_WIDTH, THUMB_HEIGHT), Image.LANCZOS)
                # Center on a fixed-size canvas
                canvas_img = Image.new("RGB", (THUMB_WIDTH, THUMB_HEIGHT), "#444444")
                x_off = (THUMB_WIDTH - img.width) // 2
                y_off = (THUMB_HEIGHT - img.height) // 2
                canvas_img.paste(img, (x_off, y_off))
                self.thumb_images.append(ImageTk.PhotoImage(canvas_img))
            self.root.after(0, self._render_page_grid)
        except Exception:
            pass

    def _render_page_grid(self):
        """Render page thumbnails in a grid on the canvas."""
        self.canvas.delete("all")
        self.page_cards.clear()

        if not self.reader:
            self.canvas.create_text(
                self.canvas.winfo_width() // 2, 100,
                text="Open a PDF file to see pages here",
                fill="#777777", font=("Segoe UI", 14)
            )
            return

        canvas_width = self.canvas.winfo_width()
        if canvas_width < 10:
            canvas_width = 800

        card_w = THUMB_WIDTH + 12
        card_h = THUMB_HEIGHT + 46
        gap = 12
        cols = max(1, (canvas_width - gap) // (card_w + gap))
        rows_needed = (len(self.reader.pages) + cols - 1) // cols

        total_grid_w = cols * (card_w + gap) - gap
        x_start = max(gap, (canvas_width - total_grid_w) // 2)

        # Remember which were selected
        selected_indices = {c.index for c in self.page_cards if c.selected} if self.page_cards else set()

        for i, page in enumerate(self.reader.pages):
            row = i // cols
            col = i % cols
            x = x_start + col * (card_w + gap)
            y = gap + row * (card_h + gap)

            box = page.mediabox
            w = float(box.width)
            h = float(box.height)
            rotation = page.get("/Rotate", 0)
            info = f"{w:.0f} x {h:.0f} pt"

            thumb = None
            if i < len(self.thumb_images):
                thumb = self.thumb_images[i]
            elif HAS_PIL:
                thumb = self._generate_placeholder_thumb(i, w, h, rotation)
                # Store to prevent garbage collection
                while len(self.thumb_images) <= i:
                    self.thumb_images.append(None)
                self.thumb_images[i] = thumb

            card = PageCard(self.canvas, i, thumb, info, x, y, self._on_card_click)
            if i in selected_indices:
                card.set_selected(True)
            self.page_cards.append(card)

        total_h = gap + rows_needed * (card_h + gap) + gap
        self.canvas.configure(scrollregion=(0, 0, canvas_width, total_h))
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

    def _select_all(self):
        for c in self.page_cards:
            c.set_selected(True)
        self._update_selection_label()

    def _update_selection_label(self):
        selected = [c for c in self.page_cards if c.selected]
        total = len(self.page_cards)
        if selected:
            nums = ", ".join(str(c.index + 1) for c in selected[:10])
            if len(selected) > 10:
                nums += f" ... (+{len(selected) - 10} more)"
            self.selection_label.config(text=f"Selected: {len(selected)}/{total} pages  [{nums}]")
        else:
            self.selection_label.config(text=f"{total} pages" if total else "")

    def _get_selected_indices(self):
        sel = tuple(c.index for c in self.page_cards if c.selected)
        if not sel:
            messagebox.showinfo("Info", "No pages selected.\nClick on page thumbnails to select them.")
        return sel

    def _require_pdf(self):
        if not self.reader:
            messagebox.showinfo("Info", "Open a PDF file first.")
            return False
        return True

    # --- File operations ---

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
            self.root.title(f"PDF Editor - {os.path.basename(path)}")
            self._render_page_grid()
            # Try real thumbnails in background
            if HAS_PDF2IMAGE:
                threading.Thread(target=self._generate_real_thumbs, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open PDF:\n{e}")

    def save_as(self):
        if not self._require_pdf():
            return
        default_name = os.path.basename(self.original_path) if self.original_path else "output.pdf"
        out = filedialog.asksaveasfilename(
            title="Save PDF As",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=default_name
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

    # --- Page operations ---

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
        writer = PdfWriter()
        rotated_count = 0
        for page in self.reader.pages:
            box = page.mediabox
            w, h = float(box.width), float(box.height)
            if w > h:
                page = page.rotate(90)
                rotated_count += 1
            writer.add_page(page)
        self._apply_writer(writer)
        messagebox.showinfo("Auto-Rotate", f"Rotated {rotated_count} landscape page(s) to portrait.")

    def delete_pages(self):
        if not self._require_pdf():
            return
        indices = self._get_selected_indices()
        if not indices:
            return
        page_nums = ", ".join(str(i + 1) for i in indices)
        if not messagebox.askyesno("Confirm Delete", f"Delete page(s) {page_nums}?"):
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
        """Merge multiple PDFs. Uses askopenfilenames which supports multi-select."""
        paths = filedialog.askopenfilenames(
            title="Select PDF files to merge (hold Ctrl to select multiple)",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not paths:
            return
        if len(paths) < 2 and not self.reader:
            messagebox.showinfo("Info",
                                "Select at least 2 PDF files to merge.\n\n"
                                "Tip: Hold Ctrl and click to select multiple files,\n"
                                "or hold Shift to select a range.")
            return

        writer = PdfWriter()
        file_list = []

        # Include currently loaded PDF first if exists
        if self.reader:
            for page in self.reader.pages:
                writer.add_page(page)
            file_list.append(f"  Current: {os.path.basename(self.original_path or 'loaded PDF')} ({len(self.reader.pages)} pages)")

        for path in paths:
            try:
                r = PdfReader(path)
                for page in r.pages:
                    writer.add_page(page)
                file_list.append(f"  + {os.path.basename(path)} ({len(r.pages)} pages)")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read {os.path.basename(path)}:\n{e}")
                return

        # Show confirmation
        msg = "Merging:\n" + "\n".join(file_list) + f"\n\nTotal: {len(writer.pages)} pages\n\nSave merged PDF?"
        if not messagebox.askyesno("Confirm Merge", msg):
            return

        out = filedialog.asksaveasfilename(
            title="Save Merged PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile="merged.pdf"
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
            "Enter page ranges separated by commas:\n"
            "  1-3, 4-6, 7-10\n\n"
            "Or a single number to split every N pages:\n"
            "  3  (splits into chunks of 3)\n\n"
            "Or type 'each' to split every page into its own file.",
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
                messagebox.showerror("Error", "Number must be at least 1.")
                return
            ranges = []
            for start in range(0, total, n):
                ranges.append((start, min(start + n, total)))
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
                messagebox.showerror("Error", "Invalid format. Use ranges like: 1-3, 4-6")
                return

        count = 0
        for idx, (start, end) in enumerate(ranges):
            writer = PdfWriter()
            for i in range(start, min(end, total)):
                writer.add_page(self.reader.pages[i])
            if len(writer.pages) > 0:
                out_path = os.path.join(outdir, f"{base}_part{idx + 1}.pdf")
                with open(out_path, "wb") as f:
                    writer.write(f)
                count += 1
        messagebox.showinfo("Split", f"Created {count} PDF file(s) in:\n{outdir}")

    def split_by_size(self):
        if not self._require_pdf():
            return
        result = simpledialog.askstring(
            "Split by Size",
            "Enter max file size per part:\n\n"
            "Examples: 1MB, 500KB, 2.5MB",
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
            messagebox.showerror("Error", "Invalid size format. Use e.g. 1MB, 500KB.")
            return
        outdir = filedialog.askdirectory(title="Select Output Directory")
        if not outdir:
            return
        base = os.path.splitext(os.path.basename(self.original_path or "output"))[0]

        total = len(self.reader.pages)
        part_num = 0
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
                if buf.tell() > max_bytes and len(pages_in_part) > 0:
                    break
                pages_in_part.append(i)
                i += 1
            part_num += 1
            writer = PdfWriter()
            for pi in pages_in_part:
                writer.add_page(self.reader.pages[pi])
            out_path = os.path.join(outdir, f"{base}_part{part_num}.pdf")
            with open(out_path, "wb") as f:
                writer.write(f)
        messagebox.showinfo("Split by Size", f"Created {part_num} PDF file(s) in:\n{outdir}")

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
        if HAS_PDF2IMAGE:
            threading.Thread(target=self._generate_real_thumbs, daemon=True).start()

    def _load_path(self, path):
        self.reader = PdfReader(path)
        self.loaded_pdf_path = path
        self.original_path = path
        self.modified = False
        self.thumb_images = []
        self.file_label.config(text=f"{os.path.basename(path)}  ({len(self.reader.pages)} pages)")
        self.root.title(f"PDF Editor - {os.path.basename(path)}")
        self._render_page_grid()
        if HAS_PDF2IMAGE:
            threading.Thread(target=self._generate_real_thumbs, daemon=True).start()


def main():
    root = tk.Tk()
    PDFEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
