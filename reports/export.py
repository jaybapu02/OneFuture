import io
from datetime import date
from xml.sax.saxutils import escape as _xml_escape

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BRAND = "#4f46e5"
BRAND_DARK = "#3730a3"
INK = "#1e293b"
MUTED = "#64748b"
LINE = "#e2e8f0"
SOFT_BG = "#f8fafc"
ROW_ALT_BG = "#f4f6fb"

MISSING = "\u2014"

PAGE_SIZE = landscape(A4)
PAGE_W, PAGE_H = PAGE_SIZE
MARGIN_LR = 12 * mm
MARGIN_TOP = 17 * mm
MARGIN_BOTTOM = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN_LR

DETAIL_HEADERS = [
    "Date", "Session", "Class", "Subject", "Topic Taught", "Trainer",
    "Location", "Period", "Start", "End",
]
DETAIL_WIDTHS_MM = [23, 17, 25, 29, 68, 32, 22, 15, 19, 20]

CENTERED_DETAIL_COLS = [(1, 1), (7, -1)]


def _fmt_date(value):
    return value.strftime("%d %b %Y") if value else MISSING


def _fmt_time(value):
    if not value:
        return MISSING
    return value.strftime("%I:%M %p").lstrip("0")


def _disp(value):
    text = str(value).strip() if value is not None else ""
    return text or MISSING


def _session_table_rows(sessions):
    """Plain-text session rows (used by the DOCX export)."""
    rows = []
    for s in sessions:
        rows.append([
            _fmt_date(s.date),
            _disp(s.session_number),
            _disp(s.school_class),
            _disp(s.subject.name),
            _disp(s.topic_taught),
            _disp(s.trainer.full_name),
            _disp(s.location),
            _disp(s.period),
            _fmt_time(s.start_time),
            _fmt_time(s.end_time),
        ])
    return rows


def _styles():
    cell_base = dict(
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor(INK),
    )
    return {
        "mast_title": ParagraphStyle(
            "MastTitle", fontName="Helvetica-Bold", fontSize=21,
            leading=24, textColor=colors.HexColor(BRAND),
        ),
        "mast_sub": ParagraphStyle(
            "MastSub", fontName="Helvetica-Bold", fontSize=9,
            leading=12, textColor=colors.HexColor(INK),
        ),
        "mast_org": ParagraphStyle(
            "MastOrg", fontName="Helvetica", fontSize=11.5,
            leading=14, textColor=colors.HexColor(MUTED),
        ),
        "mast_gen": ParagraphStyle(
            "MastGen", fontName="Helvetica", fontSize=8.5, leading=12,
            textColor=colors.HexColor(MUTED), alignment=TA_RIGHT,
        ),
        "info_label": ParagraphStyle(
            "InfoLabel", fontName="Helvetica-Bold", fontSize=8,
            leading=11, textColor=colors.HexColor(MUTED),
        ),
        "info_value": ParagraphStyle(
            "InfoValue", fontName="Helvetica", fontSize=8.5,
            leading=11, textColor=colors.HexColor(INK),
        ),
        "h2": ParagraphStyle(
            "ReportH2", fontName="Helvetica-Bold", fontSize=11.5,
            leading=14, textColor=colors.HexColor(BRAND_DARK),
            spaceBefore=12, spaceAfter=5,
        ),
        "mini_head": ParagraphStyle(
            "MiniHead", fontName="Helvetica-Bold", fontSize=8.5,
            leading=11, textColor=colors.HexColor(BRAND_DARK),
            spaceAfter=3,
        ),
        "kpi_value": ParagraphStyle(
            "KpiValue", fontName="Helvetica-Bold", fontSize=15,
            leading=18, textColor=colors.HexColor(INK),
            alignment=TA_CENTER,
        ),
        "kpi_label": ParagraphStyle(
            "KpiLabel", fontName="Helvetica", fontSize=7,
            leading=9, textColor=colors.HexColor(MUTED),
            alignment=TA_CENTER,
        ),
        "head_cell": ParagraphStyle(
            "HeadCell", fontName="Helvetica-Bold", fontSize=8.5,
            leading=11, textColor=colors.white,
        ),
        "cell": ParagraphStyle("Cell", **cell_base),
        "cell_muted": ParagraphStyle(
            "CellMuted", **{**cell_base, "textColor": colors.HexColor(MUTED)}
        ),
        "note": ParagraphStyle(
            "Note", fontName="Helvetica", fontSize=9, leading=12,
            textColor=colors.HexColor(MUTED),
        ),
    }


def _para(text, style):
    return Paragraph(_xml_escape(str(text)), style)


class ReportCanvas(pdf_canvas.Canvas):
    """Draws the repeated running head and the Page X of Y footer."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_chrome(total_pages)
            super().showPage()
        super().save()

    def _draw_chrome(self, total_pages):
        page_num = self._pageNumber
        c = self
        c.saveState()

        if page_num > 1:
            head_y = PAGE_H - 9 * mm
            c.setFont("Helvetica-Bold", 7.5)
            c.setFillColor(colors.HexColor(BRAND))
            c.drawString(MARGIN_LR, head_y, "ONEFUTURE")
            c.setFont("Helvetica", 7.5)
            c.setFillColor(colors.HexColor(MUTED))
            c.drawRightString(
                PAGE_W - MARGIN_LR, head_y,
                "Trainer Management \u00b7 Organization Report",
            )
            c.setStrokeColor(colors.HexColor(LINE))
            c.setLineWidth(0.6)
            c.line(MARGIN_LR, head_y - 2.5 * mm, PAGE_W - MARGIN_LR, head_y - 2.5 * mm)

        c.setStrokeColor(colors.HexColor(LINE))
        c.setLineWidth(0.6)
        c.line(MARGIN_LR, 13 * mm, PAGE_W - MARGIN_LR, 13 * mm)
        c.setFont("Helvetica", 7.5)
        c.setFillColor(colors.HexColor(MUTED))
        c.drawString(MARGIN_LR, 8.5 * mm, "OneFuture Organization Report")
        c.drawRightString(PAGE_W - MARGIN_LR, 8.5 * mm, f"Page {page_num} of {total_pages}")

        c.restoreState()


def _base_table_style(header_rows=1):
    return [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, header_rows), (-1, -1), colors.HexColor(INK)),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(LINE)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (0, 0), (-1, header_rows - 1), colors.HexColor(BRAND)),
        ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), colors.white),
        ("FONTNAME", (0, 0), (-1, header_rows - 1), "Helvetica-Bold"),
    ]


def _styled_table(data, col_widths, styles, center_cols=(), zebra=True):
    table = Table(data, colWidths=col_widths, repeatRows=1)
    style = _base_table_style()
    if zebra and len(data) > 1:
        style.append((
            "ROWBACKGROUNDS", (0, 1), (-1, -1),
            [colors.white, colors.HexColor(ROW_ALT_BG)],
        ))
    for start, end in center_cols:
        style.append(("ALIGN", (start, 1), (end, -1), "CENTER"))
    table.setStyle(TableStyle(style))
    return table


def _pair_table(rows, styles, label_width=40 * mm):
    data = [[_para(k, styles["info_label"]), _para(v, styles["info_value"])] for k, v in rows]
    table = Table(data, colWidths=[label_width, CONTENT_W - label_width])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(SOFT_BG)),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor(LINE)),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor(LINE)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    return table


def _summary_strip(metrics, styles):
    labels = [
        "Total Sessions", "Class Days", "Classes Covered",
    ]
    values_row = [_para(v, styles["kpi_value"]) for v in metrics]
    labels_row = [_para(lbl, styles["kpi_label"]) for lbl in labels]
    table = Table([values_row, labels_row], colWidths=[CONTENT_W / 3.0] * 3)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(SOFT_BG)),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor(LINE)),
        ("LINEBEFORE", (1, 0), (-1, -1), 0.5, colors.HexColor(LINE)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
        ("TOPPADDING", (0, 1), (-1, 1), 1),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
    ]))
    return table


def _breakdown_block(title, rows, styles):
    flow = [Paragraph(title, styles["mini_head"])]
    if rows:
        data = [[_para(r[0], styles["cell"]), _para(r[1], styles["cell"])] for r in rows]
        table = Table(data, colWidths=[56 * mm, 26 * mm])
        style = _base_table_style(header_rows=0)
        style += [
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor(ROW_ALT_BG)]),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ]
        table.setStyle(TableStyle(style))
        flow.append(table)
    else:
        flow.append(_para(MISSING, styles["note"]))
    return flow


def _breakdown_row(blocks, styles):
    cells = [[block] for block in blocks]
    table = Table([cells], colWidths=[CONTENT_W / len(blocks)] * len(blocks))
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (0, -1), 10),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return table


def _detail_table(sessions, styles):
    header = [_para(h, styles["head_cell"]) for h in DETAIL_HEADERS]
    body = []
    for s in sessions:
        topic = str(s.topic_taught or "").strip()
        location = str(s.location or "").strip()
        body.append([
            _fmt_date(s.date),
            _disp(s.session_number),
            _para(_disp(s.school_class), styles["cell"]),
            _para(_disp(s.subject.name), styles["cell"]),
            _para(topic or MISSING, styles["cell"]),
            _para(_disp(getattr(s.trainer, "full_name", None)), styles["cell"]),
            _para(location or MISSING, styles["cell_muted"]),
            _disp(s.period),
            _fmt_time(s.start_time),
            _fmt_time(s.end_time),
        ])
    table = Table(
        [header] + body,
        colWidths=[w * mm for w in DETAIL_WIDTHS_MM],
        repeatRows=1,
        splitByRow=1,
    )
    style = _base_table_style()
    style.append((
        "ROWBACKGROUNDS", (0, 1), (-1, -1),
        [colors.white, colors.HexColor(ROW_ALT_BG)],
    ))
    for start, end in CENTERED_DETAIL_COLS:
        style.append(("ALIGN", (start, 1), (end, -1), "CENTER"))
    table.setStyle(TableStyle(style))
    return table


def build_pdf(context):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=PAGE_SIZE,
        leftMargin=MARGIN_LR,
        rightMargin=MARGIN_LR,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
        title="OneFuture Organization Report",
        author="OneFuture Trainer Management",
        subject="Organization Report",
    )

    st = _styles()
    meta = context.get("report_meta", {})
    today = date.today()

    story = []

    mast_left = [
        Paragraph("ONEFUTURE", st["mast_title"]),
        Spacer(1, 2),
        Paragraph("TRAINER MANAGEMENT", st["mast_sub"]),
        Spacer(1, 5),
        Paragraph("Organization Report", st["mast_org"]),
    ]
    mast_right = Paragraph(
        f"Generated on<br/>{_xml_escape(_fmt_date(today))}", st["mast_gen"]
    )
    mast = Table([[mast_left, mast_right]], colWidths=[CONTENT_W - 60 * mm, 60 * mm])
    mast.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(mast)
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor(BRAND),
                            spaceBefore=0, spaceAfter=10))

    story.append(_pair_table([
        ("Trainer", meta.get("trainer", "All trainers")),
        ("School", meta.get("school", "All classes")),
        ("Location", meta.get("location", "All locations")),
        ("Report Period", meta.get("period", "All dates")),
        ("Generated On", _fmt_date(today)),
    ], st))

    story.append(Paragraph("Report Summary", st["h2"]))
    story.append(_summary_strip([
        context.get("total_sessions", 0),
        context.get("class_days", 0),
        context.get("classes_count", 0),
    ], st))

    blocks = [
        _breakdown_block("SESSIONS BY TRAINER",
                         [[r["trainer__full_name"], r["count"]] for r in context["by_trainer"]], st),
        _breakdown_block("SESSIONS BY CLASS",
                         [[f'{r["school_class__name"]}{" - " + r["school_class__section"] if r["school_class__section"] else ""}', r["count"]]
                          for r in context["by_class"]], st),
        _breakdown_block("SESSIONS BY SUBJECT",
                         [[r["subject__name"], r["count"]] for r in context["by_subject"]], st),
    ]
    story.append(Spacer(1, 4))
    story.append(_breakdown_row(blocks, st))

    story.append(Paragraph("Session Details", st["h2"]))
    if context["sessions"]:
        story.append(_detail_table(context["sessions"], st))
    else:
        story.append(Paragraph("No sessions match the selected filters.", st["note"]))

    doc.build(story, canvasmaker=ReportCanvas)
    return buf.getvalue()


def _shade_cell(cell, hex_color):
    fill = OxmlElement("w:shd")
    fill.set(qn("w:val"), "clear")
    fill.set(qn("w:fill"), hex_color.lstrip("#"))
    cell._tc.get_or_add_tcPr().append(fill)


def _docx_pair_table(doc, data):
    table = doc.add_table(rows=len(data), cols=len(data[0]))
    table.style = "Table Grid"
    table.autofit = True
    for r_idx, row in enumerate(data):
        for c_idx, value in enumerate(row):
            cell = table.cell(r_idx, c_idx)
            cell.text = ""
            run = cell.paragraphs[0].add_run(str(value))
            run.font.size = Pt(9)
            if r_idx == 0:
                run.bold = True
                run.font.color.rgb = RGBColor.from_string("ffffff")
                _shade_cell(cell, BRAND)


def build_docx(context):
    doc = Document()

    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = section.page_height, section.page_width
    section.left_margin = Mm(15)
    section.right_margin = Mm(15)
    section.top_margin = Mm(15)
    section.bottom_margin = Mm(15)

    doc.add_heading("OneFuture — Organization Report", 0)
    meta = doc.add_paragraph()
    run = meta.add_run(
        f"Generated on {_fmt_date(date.today())}  |  "
        f"Covering {context['total_sessions']} sessions"
    )
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor.from_string(MUTED.lstrip("#"))

    doc.add_heading("Filters", level=1)
    _docx_pair_table(doc, [["Filter", "Value"]] + [[k, v] for k, v in context["filter_summary"]])

    doc.add_heading("Summary", level=1)
    _docx_pair_table(doc, [
        ["Total Sessions", "Active Trainers", "Classes Covered", "Subjects Covered"],
        [str(context["total_sessions"]), str(context["active_trainers"]),
         str(context["classes_count"]), str(context["subjects_count"])],
    ])

    doc.add_heading("Sessions by Trainer", level=1)
    _docx_pair_table(doc, [["Trainer", "Sessions"]]
                     + [[r["trainer__full_name"], str(r["count"])] for r in context["by_trainer"]])

    doc.add_heading("Sessions by Class", level=1)
    _docx_pair_table(doc, [["Class", "Sessions"]]
                     + [[f'{r["school_class__name"]}{" - " + r["school_class__section"] if r["school_class__section"] else ""}', str(r["count"])] for r in context["by_class"]])

    doc.add_heading("Sessions by Subject", level=1)
    _docx_pair_table(doc, [["Subject", "Sessions"]]
                     + [[r["subject__name"], str(r["count"])] for r in context["by_subject"]])

    doc.add_heading("Session Details", level=1)
    if context["sessions"]:
        data = [DETAIL_HEADERS] + _session_table_rows(context["sessions"])
        table = doc.add_table(rows=len(data), cols=len(DETAIL_HEADERS))
        table.style = "Table Grid"
        table.autofit = True
        for r_idx, row in enumerate(data):
            for c_idx, value in enumerate(row):
                cell = table.cell(r_idx, c_idx)
                cell.text = ""
                run = cell.paragraphs[0].add_run(str(value))
                run.font.size = Pt(8)
                if r_idx == 0:
                    run.bold = True
                    run.font.color.rgb = RGBColor.from_string("ffffff")
                    _shade_cell(cell, BRAND)
    else:
        doc.add_paragraph("No sessions match the selected filters.")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
