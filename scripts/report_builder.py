"""
report_builder.py - DOCX machinery for the Summer Internship Project Report.

This module knows nothing about the project's content. It provides:

  * a Word document set up to the university format
    (A4, Times New Roman, 12 pt / 1.5 / justified body, 16 pt bold centred
    chapter titles, 14 pt bold main headings, 12 pt bold subheadings,
    10 pt bold figure and table captions);
  * lower-case roman page numbers for the front matter and arabic numerals
    restarting at 1 for the body, using a section break;
  * figure and table helpers that number captions per chapter and register
    them, so the List of Figures and the List of Tables are built from the
    captions that actually appear in the document;
  * a page-number resolver, so the Table of Contents / List of Figures /
    List of Tables can be filled with real page numbers on a second pass.

Used by scripts/build_report.py (Step 14).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FONT = "Times New Roman"
INK = RGBColor(0, 0, 0)
GREY = RGBColor(0x44, 0x44, 0x44)

_ROMAN = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"),
          (90, "xc"), (50, "l"), (40, "xl"), (10, "x"), (9, "ix"),
          (5, "v"), (4, "iv"), (1, "i")]


def _roman(n: int) -> str:
    out = ""
    for value, sym in _ROMAN:
        while n >= value:
            out += sym
            n -= value
    return out


# --------------------------------------------------------------------------
# low-level XML helpers
# --------------------------------------------------------------------------
def _el(tag: str, **attrs) -> OxmlElement:
    e = OxmlElement(tag)
    for k, v in attrs.items():
        e.set(qn("w:" + k), str(v))
    return e


def _field(paragraph, instr: str, placeholder: str = "1"):
    """Insert a Word field (e.g. PAGE, NUMPAGES) into a paragraph."""
    run = paragraph.add_run()
    run.font.name = FONT
    run.font.size = Pt(10)
    fld_begin = _el("w:fldChar", fldCharType="begin")
    instr_el = OxmlElement("w:instrText")
    instr_el.set(qn("xml:space"), "preserve")
    instr_el.text = instr
    fld_sep = _el("w:fldChar", fldCharType="separate")
    text_el = OxmlElement("w:t")
    text_el.text = placeholder
    fld_end = _el("w:fldChar", fldCharType="end")
    for node in (fld_begin, instr_el, fld_sep, text_el, fld_end):
        run._r.append(node)
    return run


def _page_number_format(section, fmt: str, start: int | None = None):
    """Set the page-number format (lowerRoman / decimal) for a section."""
    sect_pr = section._sectPr
    for old in sect_pr.findall(qn("w:pgNumType")):
        sect_pr.remove(old)
    pg = _el("w:pgNumType", fmt=fmt)
    if start is not None:
        pg.set(qn("w:start"), str(start))
    sect_pr.append(pg)


def _cell_shading(cell, hex_fill: str):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = _el("w:shd", val="clear", color="auto", fill=hex_fill)
    tc_pr.append(shd)


def _repeat_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tr_pr.append(_el("w:tblHeader", val="true"))


def _keep_with_next(paragraph, value: bool = True):
    p_pr = paragraph._p.get_or_add_pPr()
    for old in p_pr.findall(qn("w:keepNext")):
        p_pr.remove(old)
    p_pr.append(_el("w:keepNext", val="true" if value else "false"))


# --------------------------------------------------------------------------
# the report object
# --------------------------------------------------------------------------
class Report:
    """A university-format Word report under construction."""

    def __init__(self, outline: dict | None = None,
                 page_map: dict[str, int] | None = None,
                 front_pages: int = 0):
        self.doc = Document()
        self.page_map = page_map or {}
        self.front_pages = front_pages
        outline = outline or {}
        # entries collected on a previous pass, printed in the front matter
        self.toc_entries = outline.get("toc", [])
        self.figure_entries = outline.get("figures", [])
        self.table_entries = outline.get("tables", [])
        self._anchors: dict[str, str] = {}
        self.figures: list[tuple[str, str]] = []   # (number, caption)
        self.tables: list[tuple[str, str]] = []    # (number, caption)
        self.toc: list[tuple[int, str, str]] = []  # (level, label, key)
        self.chapter = 0
        self._fig_n = 0
        self._tab_n = 0
        self._front_matter = True
        self._need_break = False
        self._setup_styles()
        self._setup_page(self.doc.sections[0])
        _page_number_format(self.doc.sections[0], "lowerRoman", start=1)
        self._footer(self.doc.sections[0])

    # -- setup -------------------------------------------------------------
    def _setup_page(self, section):
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(3.17)
        section.right_margin = Cm(2.54)
        section.header_distance = Cm(1.27)
        section.footer_distance = Cm(1.27)

    def _footer(self, section):
        footer = section.footer
        footer.is_linked_to_previous = False
        p = footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _field(p, " PAGE ")

    def _style(self, name, size, *, bold=False, align=None, spacing=1.5,
               before=0, after=6, italic=False, color=INK, keep=False):
        styles = self.doc.styles
        try:
            st = styles[name]
        except KeyError:
            st = styles.add_style(name, 1)  # WD_STYLE_TYPE.PARAGRAPH
        st.font.name = FONT
        st.font.size = Pt(size)
        st.font.bold = bold
        st.font.italic = italic
        st.font.color.rgb = color
        rpr = st.element.get_or_add_rPr()
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is None:
            rfonts = OxmlElement("w:rFonts")
            rpr.append(rfonts)
        for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rfonts.set(qn(attr), FONT)
        pf = st.paragraph_format
        pf.line_spacing = spacing
        pf.space_before = Pt(before)
        pf.space_after = Pt(after)
        if align is not None:
            pf.alignment = align
        pf.keep_with_next = keep
        return st

    def _setup_styles(self):
        normal = self.doc.styles["Normal"]
        normal.font.name = FONT
        normal.font.size = Pt(12)
        rpr = normal.element.get_or_add_rPr()
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is None:
            rfonts = OxmlElement("w:rFonts")
            rpr.append(rfonts)
        for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rfonts.set(qn(attr), FONT)
        normal.paragraph_format.line_spacing = 1.5
        normal.paragraph_format.space_after = Pt(6)

        self._style("CRI Body", 12, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
        self._style("CRI Body Center", 12, align=WD_ALIGN_PARAGRAPH.CENTER)
        self._style("CRI Chapter", 16, bold=True,
                    align=WD_ALIGN_PARAGRAPH.CENTER, before=0, after=12,
                    keep=True)
        self._style("CRI Heading", 14, bold=True,
                    align=WD_ALIGN_PARAGRAPH.LEFT, before=12, after=6,
                    keep=True)
        self._style("CRI Subheading", 12, bold=True,
                    align=WD_ALIGN_PARAGRAPH.LEFT, before=10, after=4,
                    keep=True)
        self._style("CRI Caption", 10, bold=True,
                    align=WD_ALIGN_PARAGRAPH.CENTER, spacing=1.0,
                    before=4, after=8)
        self._style("CRI Table Caption", 10, bold=True,
                    align=WD_ALIGN_PARAGRAPH.LEFT, spacing=1.0,
                    before=10, after=4, keep=True)
        self._style("CRI Table Text", 9, align=WD_ALIGN_PARAGRAPH.LEFT,
                    spacing=1.0, before=1, after=1)
        self._style("CRI Table Head", 9, bold=True,
                    align=WD_ALIGN_PARAGRAPH.LEFT, spacing=1.0,
                    before=1, after=1)
        self._style("CRI Front Title", 16, bold=True,
                    align=WD_ALIGN_PARAGRAPH.CENTER, before=0, after=8)
        self._style("CRI Abstract", 14, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
                    spacing=2.0, after=2)
        self._style("CRI Mono", 10, align=WD_ALIGN_PARAGRAPH.LEFT,
                    spacing=1.0, before=2, after=2)
        self._style("CRI Note", 10, italic=True,
                    align=WD_ALIGN_PARAGRAPH.JUSTIFY, spacing=1.0,
                    before=2, after=8, color=GREY)
        self._style("CRI TOC1", 12, bold=True, spacing=1.15, before=6, after=2)
        self._style("CRI TOC2", 12, spacing=1.15, before=0, after=2)

    # -- structure ---------------------------------------------------------
    def page_break(self):
        p = self.doc.add_paragraph()
        p.add_run().add_break(WD_BREAK.PAGE)
        return p

    def start_body(self):
        """Close the front matter and restart page numbering at arabic 1."""
        section = self.doc.add_section(WD_SECTION.NEW_PAGE)
        self._setup_page(section)
        _page_number_format(section, "decimal", start=1)
        section.footer.is_linked_to_previous = False
        self._footer(section)
        self._front_matter = False
        self._need_break = False
        return section

    # -- text --------------------------------------------------------------
    def p(self, text="", style="CRI Body"):
        para = self.doc.add_paragraph(text, style=style)
        return para

    def rich(self, parts, style="CRI Body"):
        """parts: list of (text, bold) tuples."""
        para = self.doc.add_paragraph(style=style)
        for text, bold in parts:
            run = para.add_run(text)
            run.bold = bold
        return para

    def bullets(self, items, numbered=False, style="CRI Body"):
        for i, item in enumerate(items, start=1):
            marker = f"{i}. " if numbered else "• "
            para = self.doc.add_paragraph(style=style)
            para.paragraph_format.left_indent = Cm(0.9)
            para.paragraph_format.first_line_indent = Cm(-0.55)
            para.paragraph_format.space_after = Pt(3)
            if isinstance(item, tuple):
                head, rest = item
                run = para.add_run(marker + head)
                run.bold = True
                para.add_run(rest)
            else:
                para.add_run(marker + item)

    def code(self, lines):
        for line in lines:
            para = self.doc.add_paragraph(style="CRI Mono")
            para.paragraph_format.left_indent = Cm(0.8)
            run = para.add_run(line)
            run.font.name = "Consolas"
            rpr = run._r.get_or_add_rPr()
            rfonts = rpr.find(qn("w:rFonts"))
            if rfonts is None:
                rfonts = OxmlElement("w:rFonts")
                rpr.append(rfonts)
            for attr in ("w:ascii", "w:hAnsi", "w:cs"):
                rfonts.set(qn(attr), "Consolas")

    def note(self, text):
        return self.p(text, style="CRI Note")

    # -- headings ----------------------------------------------------------
    def chapter_title(self, number: int, name: str):
        self.chapter = number
        self._fig_n = 0
        self._tab_n = 0
        p1 = self.doc.add_paragraph(f"CHAPTER-{number}", style="CRI Chapter")
        p1.paragraph_format.page_break_before = self._need_break
        self._need_break = True
        p1.paragraph_format.space_after = Pt(2)
        _keep_with_next(p1)
        p2 = self.doc.add_paragraph(name.upper(), style="CRI Chapter")
        _keep_with_next(p2)
        key = f"CHAPTER-{number}"
        self.toc.append((0, f"CHAPTER-{number}: {name.upper()}", key))
        self._mark(p1, key)
        return p2

    def heading(self, label: str, text: str):
        p = self.doc.add_paragraph(f"{label} {text}", style="CRI Heading")
        key = f"H:{label}"
        self.toc.append((1, f"{label} {text}", key))
        self._mark(p, key)
        return p

    def subheading(self, label: str, text: str):
        full = f"{label} {text}" if label else text
        p = self.doc.add_paragraph(full, style="CRI Subheading")
        key = f"S:{label or text}"
        self.toc.append((2, full, key))
        self._mark(p, key)
        return p

    def minor(self, text: str):
        """A bold run-in heading that is NOT listed in the TOC."""
        p = self.doc.add_paragraph(text, style="CRI Subheading")
        _keep_with_next(p)
        return p

    def front_heading(self, text: str, toc: bool = True,
                      new_page: bool = True):
        p = self.doc.add_paragraph(text.upper(), style="CRI Front Title")
        p.paragraph_format.page_break_before = new_page
        key = f"F:{text}"
        if toc:
            self.toc.append((0, text.upper(), key))
        self._mark(p, key)
        return p

    def _mark(self, paragraph, key: str):
        """Remember the search string used to find this item's page number."""
        text = paragraph.text.strip()
        if key not in self._anchors:
            self._anchors[key] = text

    def page_of(self, key: str) -> str:
        """Format a resolved PDF page index as the number printed on that
        page: lower-case roman inside the front matter, arabic after it."""
        n = self.page_map.get(key)
        if not n:
            return "—"
        if self.front_pages and n <= self.front_pages:
            return _roman(n)
        return str(n - self.front_pages)

    # -- figures and tables ------------------------------------------------
    def figure(self, path: str | Path, caption: str, width_cm: float = 14.5,
               note: str | None = None):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"figure not found: {path}")
        self._fig_n += 1
        number = f"Figure {self.chapter}.{self._fig_n}"
        para = self.doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.space_before = Pt(8)
        para.paragraph_format.space_after = Pt(2)
        para.add_run().add_picture(str(path), width=Cm(width_cm))
        _keep_with_next(para)
        cap = self.doc.add_paragraph(f"{number}: {caption}", style="CRI Caption")
        self.figures.append((number, caption))
        self._mark(cap, f"FIG:{number}")
        if note:
            self.note(note)
        return number

    def table(self, caption: str, headers: list[str], rows: list[list],
              widths: list[float] | None = None, note: str | None = None,
              font_size: int | None = None):
        self._tab_n += 1
        number = f"Table {self.chapter}.{self._tab_n}"
        cap = self.doc.add_paragraph(f"{number}: {caption}",
                                     style="CRI Table Caption")
        _keep_with_next(cap)
        self.tables.append((number, caption))
        self._mark(cap, f"TAB:{number}")

        t = self.doc.add_table(rows=1, cols=len(headers))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        hdr = t.rows[0]
        _repeat_header(hdr)
        for i, h in enumerate(headers):
            cell = hdr.cells[i]
            cell.text = ""
            para = cell.paragraphs[0]
            para.style = self.doc.styles["CRI Table Head"]
            run = para.add_run(str(h))
            if font_size:
                run.font.size = Pt(font_size)
            _cell_shading(cell, "D9E2F3")
        for row in rows:
            cells = t.add_row().cells
            for i, value in enumerate(row):
                cell = cells[i]
                cell.text = ""
                para = cell.paragraphs[0]
                para.style = self.doc.styles["CRI Table Text"]
                run = para.add_run("" if value is None else str(value))
                if font_size:
                    run.font.size = Pt(font_size)
        if widths:
            for row in t.rows:
                for i, w in enumerate(widths):
                    row.cells[i].width = Cm(w)
        spacer = self.doc.add_paragraph()
        spacer.paragraph_format.space_after = Pt(2)
        spacer.paragraph_format.line_spacing = 1.0
        if note:
            self.note(note)
        return number

    # -- dotted leader lines for TOC / LOF / LOT ---------------------------
    def dotted(self, text: str, page: str, level: int = 0):
        style = "CRI TOC1" if level == 0 else "CRI TOC2"
        para = self.doc.add_paragraph(style=style)
        if level == 2:
            para.paragraph_format.left_indent = Cm(1.2)
        elif level == 1:
            para.paragraph_format.left_indent = Cm(0.6)
        tabs = para.paragraph_format.tab_stops
        tabs.add_tab_stop(Cm(15.2), 2, 1)  # RIGHT, DOTS
        para.add_run(text)
        para.add_run("\t" + page)
        return para

    def two_col_list(self, pairs, first_width: float = 3.2,
                     second_width: float = 11.8, bold_first: bool = True):
        """A borderless two-column list (abbreviations, symbols)."""
        t = self.doc.add_table(rows=0, cols=2)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        for left, right in pairs:
            cells = t.add_row().cells
            for cell, text, bold, width in (
                (cells[0], left, bold_first, first_width),
                (cells[1], right, False, second_width),
            ):
                cell.text = ""
                cell.width = Cm(width)
                para = cell.paragraphs[0]
                para.style = self.doc.styles["CRI Body"]
                para.paragraph_format.line_spacing = 1.15
                para.paragraph_format.space_after = Pt(2)
                para.alignment = WD_ALIGN_PARAGRAPH.LEFT
                run = para.add_run(text)
                run.bold = bold
        return t

    def outline(self) -> dict:
        """The structure collected on this pass, for the next pass."""
        return {"toc": list(self.toc),
                "figures": list(self.figures),
                "tables": list(self.tables)}

    def save(self, path: str | Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.doc.save(str(path))
        return path


# --------------------------------------------------------------------------
# PDF conversion + page-number resolution
# --------------------------------------------------------------------------
def docx_to_pdf(docx_path: str | Path, out_dir: str | Path) -> Path:
    docx_path, out_dir = Path(docx_path), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["soffice", "--headless", "--norestore", "--convert-to", "pdf",
         "--outdir", str(out_dir), str(docx_path)],
        check=True, capture_output=True, timeout=900,
    )
    pdf = out_dir / (docx_path.stem + ".pdf")
    if not pdf.exists():
        raise RuntimeError(f"LibreOffice did not produce {pdf}")
    return pdf


def _normalise(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", s).strip().lower()


def pdf_pages(pdf_path: str | Path) -> list[str]:
    """Return the text of every PDF page, normalised for matching."""
    from pypdf import PdfReader
    reader = PdfReader(str(pdf_path))
    return [_normalise(page.extract_text() or "") for page in reader.pages]


def pdf_page_lines(pdf_path: str | Path) -> list[list[str]]:
    """Return the normalised individual lines of every PDF page.

    Short anchors (``REFERENCES``, ``APPENDIX``, ``SYMBOLS`` ...) occur as
    ordinary words inside body text, so they are matched against whole lines
    rather than against the flattened page text."""
    from pypdf import PdfReader
    reader = PdfReader(str(pdf_path))
    out = []
    for page in reader.pages:
        raw = page.extract_text() or ""
        out.append([_normalise(line) for line in raw.splitlines()
                    if _normalise(line)])
    return out


def contents_pages(pages: list[str]) -> set[int]:
    """Indices of the Table of Contents / List of Figures / List of Tables
    pages, identified by their dot leaders.  Every heading, figure caption
    and table caption also appears on those pages, so they must be excluded
    when locating the real item."""
    return {i for i, page in enumerate(pages) if page.count("....") >= 20}


SHORT_ANCHOR = 32   # anchors at or below this length are matched line-exact


def resolve_pages(anchors: dict[str, str], pages: list[str],
                  skip: set[int] | None = None,
                  page_lines: list[list[str]] | None = None) -> dict[str, int]:
    """Map each anchor key to the 1-based PDF page index it first appears on.

    A short anchor such as ``REFERENCES`` is also a common word in running
    text, so a substring search would resolve it to the first chapter that
    happens to mention it.  Short anchors are therefore required to be a whole
    line of the page (that is, a heading), which is what ``page_lines``
    supplies.  Long anchors keep the substring search, because PDF extraction
    may wrap a long heading across two lines."""
    skip = skip or set()
    found: dict[str, int] = {}
    for key, text in anchors.items():
        needle = _normalise(text)
        if not needle:
            continue
        line_exact = page_lines is not None and len(needle) <= SHORT_ANCHOR
        if len(needle) > 70:
            needle = needle[:70]
        modes = ("exact", "prefix") if line_exact else ("substring",)
        for mode in modes:                      # prefix is the fallback for a
            for i, page in enumerate(pages):    # heading PDF extraction merged
                if i in skip:                   # with the line that follows it
                    continue
                if mode == "exact":
                    hit = any(line == needle for line in page_lines[i])
                elif mode == "prefix":
                    hit = any(line.startswith(needle) for line in page_lines[i])
                else:
                    hit = needle in page
                if hit:
                    found[key] = i + 1
                    break
            if key in found:
                break
        if key not in found and page_lines is not None:
            # The contents pages themselves are skipped above, so their own
            # titles ("TABLE OF CONTENTS", "LIST OF FIGURES", ...) are only
            # findable there.  Match those line-exact on the skipped pages.
            for i in sorted(skip):
                if any(line == needle for line in page_lines[i]):
                    found[key] = i + 1
                    break
    return found
