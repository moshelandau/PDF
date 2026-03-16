#!/usr/bin/env python3
"""Simple PDF Editor - Rotate, Delete, Merge, Split PDFs."""

import io
import os
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from PyPDF2 import PdfReader, PdfWriter


class PDFEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Editor")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)

        self.loaded_pdf_path = None
        self.reader = None

        self._build_ui()

    def _build_ui(self):
        # Menu bar
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open PDF...", command=self.open_pdf, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        self.root.config(menu=menubar)
        self.root.bind("<Control-o>", lambda e: self.open_pdf())

        # Main frame
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # Top: file info
        info_frame = ttk.LabelFrame(main, text="Current PDF", padding=5)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        self.file_label = ttk.Label(info_frame, text="No file loaded", wraplength=700)
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(info_frame, text="Open PDF", command=self.open_pdf).pack(side=tk.RIGHT)

        # Page list
        list_frame = ttk.LabelFrame(main, text="Pages", padding=5)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.page_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.page_listbox.yview)
        self.page_listbox.configure(yscrollcommand=scrollbar.set)
        self.page_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Action buttons
        btn_frame = ttk.LabelFrame(main, text="Actions", padding=5)
        btn_frame.pack(fill=tk.X)

        row1 = ttk.Frame(btn_frame)
        row1.pack(fill=tk.X, pady=2)

        ttk.Button(row1, text="Rotate Selected 90° CW", command=lambda: self.rotate_pages(90)).pack(side=tk.LEFT, padx=2)
        ttk.Button(row1, text="Rotate 180°", command=lambda: self.rotate_pages(180)).pack(side=tk.LEFT, padx=2)
        ttk.Button(row1, text="Rotate 90° CCW", command=lambda: self.rotate_pages(270)).pack(side=tk.LEFT, padx=2)
        ttk.Button(row1, text="Auto-Rotate All", command=self.auto_rotate).pack(side=tk.LEFT, padx=2)
        ttk.Button(row1, text="Delete Selected", command=self.delete_pages).pack(side=tk.LEFT, padx=2)

        row2 = ttk.Frame(btn_frame)
        row2.pack(fill=tk.X, pady=2)

        ttk.Button(row2, text="Merge PDFs...", command=self.merge_pdfs).pack(side=tk.LEFT, padx=2)
        ttk.Button(row2, text="Split by Pages...", command=self.split_by_pages).pack(side=tk.LEFT, padx=2)
        ttk.Button(row2, text="Split by Size...", command=self.split_by_size).pack(side=tk.LEFT, padx=2)
        ttk.Button(row2, text="Save As...", command=self.save_as).pack(side=tk.RIGHT, padx=2)

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
            self.file_label.config(text=f"{path}  ({len(self.reader.pages)} pages)")
            self._refresh_page_list()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open PDF:\n{e}")

    def _refresh_page_list(self):
        self.page_listbox.delete(0, tk.END)
        if not self.reader:
            return
        for i, page in enumerate(self.reader.pages):
            box = page.mediabox
            w = float(box.width)
            h = float(box.height)
            rotation = page.get("/Rotate", 0)
            self.page_listbox.insert(
                tk.END,
                f"Page {i + 1:>4d}   |   {w:.0f} x {h:.0f} pt   |   Rotation: {rotation}°"
            )

    def _get_selected_indices(self):
        sel = self.page_listbox.curselection()
        if not sel:
            messagebox.showinfo("Info", "No pages selected. Select pages in the list first.")
        return sel

    def _require_pdf(self):
        if not self.reader:
            messagebox.showinfo("Info", "Open a PDF file first.")
            return False
        return True

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
        """Auto-rotate pages so that width < height (portrait orientation).
        Landscape pages get rotated 90° clockwise."""
        if not self._require_pdf():
            return

        writer = PdfWriter()
        rotated_count = 0
        for page in self.reader.pages:
            box = page.mediabox
            w = float(box.width)
            h = float(box.height)
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

    def merge_pdfs(self):
        paths = filedialog.askopenfilenames(
            title="Select PDFs to Merge",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not paths:
            return

        writer = PdfWriter()

        # If a PDF is already loaded, include it first
        if self.reader:
            for page in self.reader.pages:
                writer.add_page(page)

        for path in paths:
            try:
                r = PdfReader(path)
                for page in r.pages:
                    writer.add_page(page)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read {os.path.basename(path)}:\n{e}")
                return

        out = filedialog.asksaveasfilename(
            title="Save Merged PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not out:
            return

        with open(out, "wb") as f:
            writer.write(f)
        messagebox.showinfo("Merge", f"Merged {len(writer.pages)} pages saved to:\n{out}")
        self._load_path(out)

    def split_by_pages(self):
        if not self._require_pdf():
            return

        total = len(self.reader.pages)
        result = simpledialog.askstring(
            "Split by Pages",
            f"Total pages: {total}\n\n"
            "Enter page ranges separated by commas.\n"
            "Examples:\n"
            "  1-3, 4-6, 7-10\n"
            "  1, 2-5, 6-10\n"
            "  (or a single number like 3 to split every 3 pages)",
            parent=self.root
        )
        if not result:
            return

        result = result.strip()
        outdir = filedialog.askdirectory(title="Select Output Directory")
        if not outdir:
            return

        base = os.path.splitext(os.path.basename(self.loaded_pdf_path))[0]

        # Check if it's a single number (split every N pages)
        if result.isdigit():
            n = int(result)
            if n < 1:
                messagebox.showerror("Error", "Number must be at least 1.")
                return
            ranges = []
            for start in range(0, total, n):
                end = min(start + n, total)
                ranges.append((start, end))
        else:
            # Parse comma-separated ranges
            ranges = []
            for part in result.split(","):
                part = part.strip()
                if "-" in part:
                    a, b = part.split("-", 1)
                    a, b = int(a.strip()) - 1, int(b.strip())
                    ranges.append((a, b))
                else:
                    p = int(part.strip()) - 1
                    ranges.append((p, p + 1))

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
            "Enter max file size per split.\n"
            "Examples: 1MB, 500KB, 5MB",
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

        base = os.path.splitext(os.path.basename(self.loaded_pdf_path))[0]
        self._split_by_size_impl(max_bytes, outdir, base)

    def _split_by_size_impl(self, max_bytes, outdir, base):
        total = len(self.reader.pages)
        part_num = 0
        i = 0

        while i < total:
            pages_in_part = [i]
            i += 1

            while i < total:
                # Test if adding next page exceeds limit
                test_writer = PdfWriter()
                for pi in pages_in_part + [i]:
                    test_writer.add_page(self.reader.pages[pi])

                buf = io.BytesIO()
                test_writer.write(buf)
                size = buf.tell()

                if size > max_bytes and len(pages_in_part) > 0:
                    break
                pages_in_part.append(i)
                i += 1

            # Write this part
            part_num += 1
            writer = PdfWriter()
            for pi in pages_in_part:
                writer.add_page(self.reader.pages[pi])

            out_path = os.path.join(outdir, f"{base}_part{part_num}.pdf")
            with open(out_path, "wb") as f:
                writer.write(f)

        messagebox.showinfo("Split by Size", f"Created {part_num} PDF file(s) in:\n{outdir}")

    def save_as(self):
        if not self._require_pdf():
            return

        out = filedialog.asksaveasfilename(
            title="Save PDF As",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=os.path.basename(self.loaded_pdf_path) if self.loaded_pdf_path else "output.pdf"
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

    def _apply_writer(self, writer):
        """Save writer to a temp location and reload."""
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        writer.write(tmp)
        tmp.close()
        self._load_path(tmp.name)
        # Keep original path for display
        if self.loaded_pdf_path and not self.loaded_pdf_path.startswith(tempfile.gettempdir()):
            self.file_label.config(
                text=f"{self.loaded_pdf_path}  ({len(self.reader.pages)} pages) [modified]"
            )

    def _load_path(self, path):
        self.reader = PdfReader(path)
        self.loaded_pdf_path = path
        self.file_label.config(text=f"{path}  ({len(self.reader.pages)} pages)")
        self._refresh_page_list()


def main():
    root = tk.Tk()
    PDFEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
