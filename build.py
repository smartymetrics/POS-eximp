from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle, Polygon, Group
from reportlab.graphics import renderPDF
import io

# Backwards-compat helper: add drawPolygon to Canvas if missing
from reportlab.pdfgen import canvas as _rl_canvas
if not hasattr(_rl_canvas.Canvas, "drawPolygon"):
    def _drawPolygon(self, pts, fill=1, stroke=1):
        p = self.beginPath()
        p.moveTo(pts[0], pts[1])
        for i in range(2, len(pts), 2):
            p.lineTo(pts[i], pts[i+1])
        p.close()
        self.drawPath(p, fill=fill, stroke=stroke)
    _rl_canvas.Canvas.drawPolygon = _drawPolygon

# ─── COLOR PALETTE ────────────────────────────────────────────────────────────
GOLD       = colors.HexColor("#C47D0A")
GOLD_LIGHT = colors.HexColor("#F5E6C8")
GOLD_PALE  = colors.HexColor("#FDF8EE")
DARK       = colors.HexColor("#0B0C0F")
SURFACE    = colors.HexColor("#111317")
CARD       = colors.HexColor("#1A1D24")
BORDER     = colors.HexColor("#2D2F36")
TEXT       = colors.HexColor("#1A2130")
SUB        = colors.HexColor("#556677")
MUTED      = colors.HexColor("#99AABB")
WHITE      = colors.white
GREEN      = colors.HexColor("#10B981")
RED        = colors.HexColor("#EF4444")
BLUE       = colors.HexColor("#3B82F6")
YELLOW     = colors.HexColor("#F59E0B")
LIGHT_BG   = colors.HexColor("#F8F9FB")
SECTION_BG = colors.HexColor("#FDF6E8")

W, H = A4

# ─── STYLES ──────────────────────────────────────────────────────────────────
def make_styles():
    s = getSampleStyleSheet()

    def add(name, **kw):
        s.add(ParagraphStyle(name=name, **kw))

    add("Cover_Title",
        fontName="Helvetica-Bold", fontSize=38, leading=46,
        textColor=WHITE, alignment=TA_CENTER, spaceAfter=8)
    add("Cover_Sub",
        fontName="Helvetica", fontSize=15, leading=20,
        textColor=GOLD_LIGHT, alignment=TA_CENTER, spaceAfter=4)
    add("Cover_Note",
        fontName="Helvetica", fontSize=11, leading=15,
        textColor=colors.HexColor("#CCCCCC"), alignment=TA_CENTER)

    add("ChapterNum",
        fontName="Helvetica-Bold", fontSize=11, leading=14,
        textColor=GOLD, spaceAfter=4)
    add("ChapterTitle",
        fontName="Helvetica-Bold", fontSize=22, leading=28,
        textColor=TEXT, spaceAfter=6)
    add("SectionTitle",
        fontName="Helvetica-Bold", fontSize=14, leading=18,
        textColor=TEXT, spaceBefore=14, spaceAfter=6)
    add("SubSection",
        fontName="Helvetica-Bold", fontSize=11, leading=14,
        textColor=GOLD, spaceBefore=10, spaceAfter=4)
    add("Body",
        fontName="Helvetica", fontSize=10, leading=15,
        textColor=TEXT, spaceAfter=6, alignment=TA_JUSTIFY)
    add("BodySmall",
        fontName="Helvetica", fontSize=9, leading=13,
        textColor=SUB, spaceAfter=4)
    add("BulletItem",
        fontName="Helvetica", fontSize=10, leading=14,
        textColor=TEXT, leftIndent=16, spaceAfter=3,
        bulletIndent=4, bulletFontName="Helvetica")
    add("StepItem",
        fontName="Helvetica", fontSize=10, leading=14,
        textColor=TEXT, leftIndent=20, spaceAfter=4)
    add("Caption",
        fontName="Helvetica-Oblique", fontSize=9, leading=12,
        textColor=MUTED, alignment=TA_CENTER, spaceAfter=8)
    add("TOC_H1",
        fontName="Helvetica-Bold", fontSize=11, leading=16,
        textColor=TEXT, spaceAfter=2)
    add("TOC_H2",
        fontName="Helvetica", fontSize=10, leading=14,
        textColor=SUB, leftIndent=16, spaceAfter=1)
    add("NoteBox",
        fontName="Helvetica-Oblique", fontSize=9.5, leading=14,
        textColor=colors.HexColor("#5A4000"), spaceAfter=6,
        leftIndent=8, rightIndent=8)
    add("CodeInline",
        fontName="Courier", fontSize=9, leading=13,
        textColor=colors.HexColor("#8B1A1A"), backColor=colors.HexColor("#FEF3F2"))
    add("TableHead",
        fontName="Helvetica-Bold", fontSize=9, leading=12,
        textColor=WHITE, alignment=TA_CENTER)
    add("TableCell",
        fontName="Helvetica", fontSize=9, leading=12,
        textColor=TEXT)
    add("TableCellBold",
        fontName="Helvetica-Bold", fontSize=9, leading=12,
        textColor=TEXT)
    add("PageHeader",
        fontName="Helvetica", fontSize=8, leading=10,
        textColor=MUTED)
    return s

S = make_styles()

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def sp(n=6):   return Spacer(1, n)
def hr(col=BORDER, thick=0.5):
    return HRFlowable(width="100%", thickness=thick, color=col, spaceAfter=6, spaceBefore=6)

def para(text, style="Body"):
    return Paragraph(text, S[style])

def bullet(text):
    return Paragraph(f"<bullet>&bull;</bullet> {text}", S["BulletItem"])

def step(n, text):
    return Paragraph(f"<b>Step {n}.</b> {text}", S["StepItem"])

def subhead(text):
    return Paragraph(text, S["SubSection"])

def note(text):
    return NoteBoxFlowable(text)

def code(text):
    return Paragraph(f'<font name="Courier" size="9" color="#8B1A1A">{text}</font>', S["Body"])

# ─── CUSTOM FLOWABLES ─────────────────────────────────────────────────────────
class NoteBoxFlowable(Flowable):
    def __init__(self, text, width=None):
        super().__init__()
        self.text = text
        self._width = width

    def wrap(self, availWidth, availHeight):
        self.avail = availWidth
        return availWidth, 0

    def draw(self):
        w = self._width or self.avail
        c = self.canv
        # Background
        c.setFillColor(SECTION_BG)
        c.setStrokeColor(GOLD)
        c.setLineWidth(1)
        c.roundRect(0, -4, w, 28, 4, fill=1, stroke=1)
        # Icon
        c.setFillColor(GOLD)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(8, 6, "ℹ")
        # Text
        c.setFillColor(colors.HexColor("#5A4000"))
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(22, 6, self.text[:110])

    def wrap(self, availWidth, availHeight):
        self.avail = availWidth
        return availWidth, 32


class ColorBar(Flowable):
    """A horizontal colored bar used as chapter header background"""
    def __init__(self, height=4, color=GOLD):
        super().__init__()
        self.bar_height = height
        self.color = color

    def wrap(self, availWidth, availHeight):
        self.avail = availWidth
        return availWidth, self.bar_height + 6

    def draw(self):
        c = self.canv
        c.setFillColor(self.color)
        c.rect(0, 0, self.avail, self.bar_height, fill=1, stroke=0)


class ChapterHeader(Flowable):
    def __init__(self, num, title, subtitle=""):
        super().__init__()
        self.num = num
        self.title = title
        self.subtitle = subtitle

    def wrap(self, availWidth, availHeight):
        self.avail = availWidth
        return availWidth, 72

    def draw(self):
        c = self.canv
        w = self.avail
        # Background rect
        c.setFillColor(SECTION_BG)
        c.setStrokeColor(GOLD)
        c.setLineWidth(1.5)
        c.roundRect(0, 2, w, 68, 6, fill=1, stroke=1)
        # Gold accent bar left
        c.setFillColor(GOLD)
        c.rect(0, 2, 5, 68, fill=1, stroke=0)
        # Chapter number
        c.setFillColor(GOLD)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(16, 54, f"CHAPTER {self.num}")
        # Title
        c.setFillColor(TEXT)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(16, 30, self.title)
        # Subtitle
        if self.subtitle:
            c.setFillColor(SUB)
            c.setFont("Helvetica-Oblique", 9)
            c.drawString(16, 14, self.subtitle)


class StatusBadge(Flowable):
    """Small inline status badge"""
    COLORS = {
        "Achieved": (GREEN, WHITE),
        "On Track": (BLUE, WHITE),
        "At Risk":  (YELLOW, TEXT),
        "Behind":   (RED, WHITE),
    }
    def __init__(self, status):
        super().__init__()
        self.status = status
        self.bg, self.fg = self.COLORS.get(status, (MUTED, WHITE))

    def wrap(self, aw, ah):
        return 70, 16

    def draw(self):
        c = self.canv
        c.setFillColor(self.bg)
        c.roundRect(0, 0, 70, 14, 4, fill=1, stroke=0)
        c.setFillColor(self.fg)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(35, 3, self.status.upper())


# ─── MERMAID-STYLE DIAGRAM DRAWABLES ─────────────────────────────────────────
class FlowDiagram(Flowable):
    """Generic top-down flow diagram"""
    def __init__(self, nodes, arrows, width=480, height=None):
        super().__init__()
        self.nodes = nodes   # [(x,y,w,h,label,color,shape)]
        self.arrows = arrows # [(from_idx, to_idx, label)]
        self._w = width
        self._h = height or (max(n[1] for n in nodes) + max(n[3] for n in nodes) + 20)

    def wrap(self, aw, ah):
        return self._w, self._h

    def draw(self):
        c = self.canv
        centers = {}
        for i, (x, y, w, h, label, col, shape) in enumerate(self.nodes):
            cx, cy = x + w/2, self._h - y - h/2
            centers[i] = (cx, cy, w, h)
            c.setFillColor(col)
            c.setStrokeColor(WHITE)
            c.setLineWidth(1)
            if shape == "diamond":
                pts = [cx, cy+h/2, cx+w/2, cy, cx, cy-h/2, cx-w/2, cy]
                c.drawPolygon(pts, fill=1, stroke=1)
            elif shape == "round":
                c.roundRect(x, self._h-y-h, w, h, h/2, fill=1, stroke=1)
            else:
                c.roundRect(x, self._h-y-h, w, h, 5, fill=1, stroke=1)
            # Text
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", 8)
            lines = label.split("\n")
            lh = 11
            start_y = cy + (len(lines)-1)*lh/2 - 2
            for ln in lines:
                c.drawCentredString(cx, start_y, ln)
                start_y -= lh

        for (fi, ti, lbl) in self.arrows:
            fx, fy, fw, fh = centers[fi]
            tx, ty, tw, th = centers[ti]
            # Simple vertical arrow
            c.setStrokeColor(GOLD)
            c.setFillColor(GOLD)
            c.setLineWidth(1.5)
            sy = fy - fh/2
            ey = ty + th/2
            c.line(fx, sy, tx, ey+6)
            # Arrowhead
            aw2 = 5
            c.drawPolygon([tx-aw2, ey+6, tx+aw2, ey+6, tx, ey], fill=1, stroke=0)
            if lbl:
                c.setFillColor(GOLD)
                c.setFont("Helvetica-Oblique", 7)
                c.drawCentredString((fx+tx)/2+20, (sy+ey)/2, lbl)


class PortalArchDiagram(Flowable):
    """Portal architecture overview diagram"""
    def __init__(self):
        super().__init__()

    def wrap(self, aw, ah):
        self._w = aw
        return aw, 260

    def draw(self):
        c = self.canv
        w = self._w
        H = 260

        # Title
        c.setFillColor(DARK)
        c.roundRect(0, 0, w, H, 8, fill=1, stroke=0)
        c.setFillColor(GOLD)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(w/2, H-18, "HRM PORTAL — SYSTEM OVERVIEW")

        # Three columns: Roles | Portal Modules | Data Layer
        col_w = (w - 40) / 3
        col_positions = [10, 10 + col_w + 10, 10 + 2*(col_w + 10)]

        labels = ["USER ROLES", "PORTAL MODULES", "DATA / INTEGRATIONS"]
        role_items = ["HR Admin", "Manager", "Staff"]
        module_items = ["Dashboard & Reports", "Recruitment & ATS", "People & Org", "Time & Attendance",
                        "Leave Management", "Performance & KPIs", "Payroll & Compensation",
                        "Documents & Compliance", "Engagement & Culture"]
        data_items = ["Sales DB", "Attendance Logs", "Payroll Engine", "Leave Policies",
                      "KPI Sync Engine", "Audit Logs"]

        for ci, (col_x, col_label, items) in enumerate(zip(
                col_positions, labels,
                [role_items, module_items, data_items])):
            # Column header
            c.setFillColor(GOLD)
            c.roundRect(col_x, H-42, col_w, 18, 4, fill=1, stroke=0)
            c.setFillColor(DARK)
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(col_x + col_w/2, H-35, col_label)

            # Items
            item_h = min(22, (H - 56) / max(len(items), 1))
            for ii, item in enumerate(items):
                iy = H - 52 - ii * (item_h + 3)
                col_map = [BLUE, colors.HexColor("#059669"), colors.HexColor("#7C3AED")]
                c.setFillColor(col_map[ci])
                c.setFillAlpha(0.85)
                c.roundRect(col_x + 2, iy - item_h + 4, col_w - 4, item_h, 4, fill=1, stroke=0)
                c.setFillAlpha(1)
                c.setFillColor(WHITE)
                c.setFont("Helvetica", 7.5)
                c.drawCentredString(col_x + col_w/2, iy - item_h + 9, item)

        # Connecting arrows (simple)
        arrow_y = H / 2
        for cx in [col_positions[0] + col_w + 2, col_positions[1] + col_w + 2]:
            c.setStrokeColor(GOLD)
            c.setLineWidth(1.5)
            c.line(cx, arrow_y, cx + 7, arrow_y)
            c.setFillColor(GOLD)
            c.drawPolygon([cx+7, arrow_y+4, cx+7, arrow_y-4, cx+12, arrow_y], fill=1, stroke=0)


class KPIFlowDiagram(Flowable):
    """KPI automated grading flow"""
    def __init__(self):
        super().__init__()

    def wrap(self, aw, ah):
        self._w = min(aw, 480)
        return self._w, 310

    def draw(self):
        c = self.canv
        w = self._w
        H = 310

        nodes = [
            # (label, x, y, w, h, bg, shape)
            ("HR Creates\nKPI Template", w/2-60, 280, 120, 34, GOLD, "rect"),
            ("Assign Goal\nto Staff / Dept", w/2-60, 230, 120, 34, BLUE, "rect"),
            ("Measurement\nSource?", w/2-55, 172, 110, 38, colors.HexColor("#7C3AED"), "diamond"),
            ("Manual", w/2-170, 120, 90, 28, MUTED, "round"),
            ("Automated", w/2+80, 120, 90, 28, GREEN, "round"),
            ("Manager\nEnters Actual", w/2-170, 65, 90, 34, SUB, "rect"),
            ("Sync Engine\nRuns nightly / \n🔄 Sync Performance", w/2+80, 52, 90, 50, GREEN, "rect"),
            ("Achievement\n% Calculated", w/2-60, 5, 120, 34, GOLD, "rect"),
        ]

        def draw_node(label, x, y, nw, nh, bg, shape):
            c.setFillColor(bg)
            c.setStrokeColor(colors.HexColor("#FFFFFF40"))
            c.setLineWidth(0.5)
            if shape == "diamond":
                pts = [x+nw/2, y+nh, x+nw, y+nh/2, x+nw/2, y, x, y+nh/2]
                c.drawPolygon(pts, fill=1, stroke=1)
            elif shape == "round":
                c.roundRect(x, y, nw, nh, nh/2, fill=1, stroke=1)
            else:
                c.roundRect(x, y, nw, nh, 6, fill=1, stroke=1)
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", 8)
            lines = label.split("\n")
            cy = y + nh/2 + (len(lines)-1)*5
            for ln in lines:
                c.drawCentredString(x+nw/2, cy, ln)
                cy -= 10

        # draw nodes
        for (label, x, y, nw, nh, bg, shape) in nodes:
            draw_node(label, x, y, nw, nh, bg, shape)

        # arrows
        def arrow(x1, y1, x2, y2, lbl=""):
            c.setStrokeColor(GOLD)
            c.setFillColor(GOLD)
            c.setLineWidth(1.2)
            c.line(x1, y1, x2, y2+5)
            c.drawPolygon([x2-4, y2+5, x2+4, y2+5, x2, y2], fill=1, stroke=0)
            if lbl:
                c.setFont("Helvetica-Oblique", 7)
                c.drawString((x1+x2)/2+4, (y1+y2)/2, lbl)

        cx = w/2
        arrow(cx, 280, cx, 264)           # template -> goal
        arrow(cx, 230, cx, 210)           # goal -> source?
        # branches
        arrow(cx-15, 172, w/2-125, 148, "Manual")
        arrow(cx+15, 172, w/2+125, 148, "Auto")
        arrow(w/2-125, 120, w/2-125, 99)
        arrow(w/2+125, 120, w/2+125, 102)
        # converge
        arrow(w/2-80, 65, cx-30, 39)
        arrow(w/2+125, 52, cx+30, 39)


class LeaveFlowDiagram(Flowable):
    """Leave approval workflow"""
    def __init__(self):
        super().__init__()

    def wrap(self, aw, ah):
        self._w = min(aw, 460)
        return self._w, 200

    def draw(self):
        c = self.canv
        w = self._w
        H = 200
        bw, bh = 100, 30
        gap = (w - 5*bw) / 6

        stages = [
            ("Staff Submits\nLeave Form", BLUE),
            ("Pending\nQueue", YELLOW),
            ("HR Reviews\n& Decides", GOLD),
            ("Approved /\nRejected", GREEN),
            ("Balance\nUpdated", colors.HexColor("#059669")),
        ]

        y = H/2 - bh/2
        xs = [gap + i*(bw+gap) for i in range(5)]

        for i, ((label, col), x) in enumerate(zip(stages, xs)):
            c.setFillColor(col)
            c.setStrokeColor(WHITE)
            c.setLineWidth(0.5)
            c.roundRect(x, y, bw, bh, 5, fill=1, stroke=1)
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", 7.5)
            lines = label.split("\n")
            ty = y + bh/2 + (len(lines)-1)*5
            for ln in lines:
                c.drawCentredString(x+bw/2, ty, ln)
                ty -= 10
            # Arrow
            if i < 4:
                ax = x + bw + 2
                ay = y + bh/2
                c.setStrokeColor(GOLD)
                c.setFillColor(GOLD)
                c.setLineWidth(1.5)
                c.line(ax, ay, ax + gap - 5, ay)
                c.drawPolygon([ax+gap-5, ay+3, ax+gap-5, ay-3, ax+gap, ay], fill=1, stroke=0)

        # Note about bulk approve
        c.setFillColor(SECTION_BG)
        c.roundRect(xs[2]-5, y-40, bw+10, 24, 4, fill=1, stroke=0)
        c.setFillColor(GOLD)
        c.setFont("Helvetica-Oblique", 7.5)
        c.drawCentredString(xs[2]+bw/2, y-30, "Use Bulk Approve for")
        c.drawCentredString(xs[2]+bw/2, y-40, "multiple pending requests")


class SidebarMapDiagram(Flowable):
    """Visual sidebar section map"""
    def __init__(self):
        super().__init__()

    def wrap(self, aw, ah):
        self._w = aw
        return aw, 300

    def draw(self):
        c = self.canv
        w = self._w
        H = 300

        sections = [
            ("Overview",             ["HR Overview", "Task Manager"],                      GOLD),
            ("Recruitment",          ["Jobs", "Applications", "ATS Pipeline", "Offers"],   BLUE),
            ("People & Org",         ["Employees", "Org Chart", "Departments"],             colors.HexColor("#059669")),
            ("Time & Attendance",    ["Attendance", "Timesheets", "Shift Scheduling"],      colors.HexColor("#7C3AED")),
            ("Leave",                ["Leave Requests", "Leave Policies", "Accrual"],       colors.HexColor("#0891B2")),
            ("Performance",          ["Goals & OKRs", "KPI Library", "360° Reviews"],       GOLD),
            ("Compensation",         ["Payroll", "Bonuses", "Benefits"],                    colors.HexColor("#DC2626")),
            ("Documents/Compliance", ["Contract Kitchen", "HR Letters", "Grievances"],      colors.HexColor("#6D28D9")),
            ("Administration",       ["Reports", "Users", "Audit Logs", "Settings"],        SUB),
        ]

        cols = 3
        rows = 3
        bw = (w - 30) / cols
        bh = (H - 20) / rows

        for i, (sec, items, col) in enumerate(sections):
            row = i // cols
            ci  = i % cols
            x = 10 + ci * bw
            y = H - 10 - (row+1)*bh

            c.setFillColor(col)
            c.setFillAlpha(0.12)
            c.roundRect(x+2, y+2, bw-4, bh-4, 6, fill=1, stroke=0)
            c.setFillAlpha(1)
            c.setStrokeColor(col)
            c.setLineWidth(1)
            c.roundRect(x+2, y+2, bw-4, bh-4, 6, fill=0, stroke=1)

            # Section header
            c.setFillColor(col)
            c.roundRect(x+2, y+bh-22, bw-4, 18, 4, fill=1, stroke=0)
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(x+bw/2, y+bh-14, sec.upper())

            # Items
            c.setFont("Helvetica", 7.5)
            c.setFillColor(TEXT)
            item_y = y + bh - 32
            for it in items[:4]:
                c.setFillColor(col)
                c.circle(x+12, item_y+3, 2, fill=1, stroke=0)
                c.setFillColor(TEXT)
                c.drawString(x+18, item_y, it)
                item_y -= 13


class OnboardingFlow(Flowable):
    def __init__(self):
        super().__init__()

    def wrap(self, aw, ah):
        self._w = aw
        return aw, 100

    def draw(self):
        c = self.canv
        w = self._w
        H = 100
        steps = [
            ("Invite\nEmployee", GOLD),
            ("Fill Bio\nData", BLUE),
            ("Sign\nContract", GREEN),
            ("IT Access\nSetup", colors.HexColor("#7C3AED")),
            ("Complete\nChecklist", GREEN),
            ("Probation\nStarts", GOLD),
        ]
        bw = (w - 20) / len(steps)
        y = 30
        bh = 40
        for i, (label, col) in enumerate(steps):
            x = 10 + i * bw
            c.setFillColor(col)
            c.roundRect(x+2, y, bw-4, bh, 5, fill=1, stroke=0)
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", 7.5)
            lines = label.split("\n")
            ty = y + bh/2 + (len(lines)-1)*4.5
            for ln in lines:
                c.drawCentredString(x+bw/2, ty, ln)
                ty -= 9
            if i < len(steps)-1:
                ax = x + bw
                ay = y + bh/2
                c.setFillColor(GOLD)
                c.drawPolygon([ax, ay-3, ax, ay+3, ax+6, ay], fill=1, stroke=0)
        # Step numbers
        for i in range(len(steps)):
            x = 10 + i * bw + bw/2
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(x, 12, f"Step {i+1}")


class RecruitmentPipeline(Flowable):
    def __init__(self):
        super().__init__()

    def wrap(self, aw, ah):
        self._w = aw
        return aw, 90

    def draw(self):
        c = self.canv
        w = self._w
        H = 90
        stages = [
            ("Applied", 100, BLUE),
            ("Shortlisted", 80, colors.HexColor("#059669")),
            ("Interview", 60, GOLD),
            ("Offer\nSent", 40, colors.HexColor("#7C3AED")),
            ("Hired", 25, GREEN),
        ]
        total = sum(n for _, n, _ in stages)
        bh = 50
        x = 10
        for label, n, col in stages:
            bw = (w - 20) * n / total
            c.setFillColor(col)
            c.roundRect(x, 20, bw, bh, 4, fill=1, stroke=0)
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", 7.5)
            if bw > 30:
                lines = label.split("\n")
                ty = 20 + bh/2 + (len(lines)-1)*4
                for ln in lines:
                    c.drawCentredString(x+bw/2, ty, ln)
                    ty -= 9
            # Count
            c.setFont("Helvetica", 7)
            c.drawCentredString(x+bw/2, 12, str(n))
            x += bw
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Oblique", 7)
        c.drawCentredString(w/2, 5, "Typical funnel: numbers represent relative candidate count at each stage")


# ─── TABLES ──────────────────────────────────────────────────────────────────
def make_table(headers, rows, col_widths=None):
    data = [[Paragraph(h, S["TableHead"]) for h in headers]]
    for row in rows:
        data.append([Paragraph(str(c), S["TableCell"]) for c in row])

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), GOLD),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, LIGHT_BG]),
        ("GRID",        (0,0), (-1,-1), 0.4, BORDER),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",  (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING",(0,0), (-1,-1), 8),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,0), 9),
        ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",    (0,1), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,0), (-1,0), [GOLD]),
        ("TEXTCOLOR",   (0,0), (-1,0), WHITE),
    ]))
    return t


def role_table():
    headers = ["Role", "Access Level", "Key Capabilities"]
    rows = [
        ["HR Admin", "Full Access", "All modules, system settings, user management, reports"],
        ["Manager",  "Departmental", "View own team, approve leave/timesheets, update KPI actuals, review performance"],
        ["Staff",    "Personal",     "Own profile, leave requests, payslips, bio data, goals view"],
    ]
    return make_table(headers, rows, [80, 90, None])


def kpi_sources_table():
    headers = ["Measurement Source", "What It Counts", "Linked Data"]
    rows = [
        ["sales_revenue",       "Total invoiced sales by rep",       "Invoices table (sales_rep_id)"],
        ["sales_deals_closed",  "Closed deals in period",            "Deals / opportunities"],
        ["sales_collection_rate","% invoices collected",             "Payments vs invoices"],
        ["mkt_leads_added",     "New marketing contacts",            "marketing_contacts (created_by)"],
        ["mkt_lead_conversion", "Leads converted to clients",        "Contact status transitions"],
        ["ops_appointments",    "Appointments completed",            "appointments table"],
        ["admin_ticket_esc",    "Support tickets escalated",         "support_tickets (resolved_at)"],
        ["manual",              "Manager enters actual manually",    "No automation — HR/manager input required"],
    ]
    return make_table(headers, rows, [120, 140, None])


def troubleshoot_table():
    headers = ["Symptom", "Likely Cause", "Resolution"]
    rows = [
        ["KPI value stays 0",       "Automated source not synced",          "Click 🔄 Sync Performance; confirm migrations deployed"],
        ["Sales KPI = 0",           "Missing sales_rep_id mapping",          "Confirm the staff-to-sales_rep_id mapping exists in the backend system"],
        ["Old contacts not counted","created_by = NULL on old records",      "Dev must backfill; new contacts will auto-assign"],
        ["Tickets miscounted",      "resolved_at column missing",            "Dev must apply migration; rerun sync"],
        ["Score shows 0 after sync","Wrong period / month selected on goal", "Edit goal → check Performance Period matches current month"],
        ["Cannot create goal",      "No KPI templates exist",                "Go to KPI Library → Define New KPI first"],
    ]
    return make_table(headers, rows)


def permissions_table():
    headers = ["Action", "HR Admin", "Manager", "Staff"]
    check = "✓"
    cross = "—"
    rows = [
        ["Create KPI Templates",       check, cross, cross],
        ["Create & Assign Goals",      check, cross, cross],
        ["Update Manual KPI Actuals",  check, check, cross],
        ["Trigger Sync Performance",   check, cross, cross],
        ["Approve Leave Requests",     check, check, cross],
        ["Invite / Deactivate Users",  check, cross, cross],
        ["Run Payroll",                check, cross, cross],
        ["View Own Payslip",           check, check, check],
        ["Submit Leave Request",       check, check, check],
        ["View Own Goals",             check, check, check],
        ["Edit Own Profile",           check, check, check],
        ["Run HR Reports",             check, check, cross],
        ["Access Audit Logs",          check, cross, cross],
    ]
    t = make_table(headers, rows, [None, 60, 60, 60])
    return t


# ─── PAGE TEMPLATE ────────────────────────────────────────────────────────────
def make_header_footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    # Header line
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.4)
    canvas.line(1.5*cm, h - 1.2*cm, w - 1.5*cm, h - 1.2*cm)
    canvas.setFillColor(GOLD)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(1.5*cm, h - 1.0*cm, "HRM PORTAL")
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(w - 1.5*cm, h - 1.0*cm, "HR User Guide")

    # Footer
    canvas.setStrokeColor(BORDER)
    canvas.line(1.5*cm, 1.2*cm, w - 1.5*cm, 1.2*cm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(w/2, 0.7*cm, f"Page {doc.page}")
    canvas.restoreState()


# ─── COVER PAGE ──────────────────────────────────────────────────────────────
class CoverPage(Flowable):
    def wrap(self, aw, ah):
        return aw, ah

    def draw(self):
        c = self.canv
        w, h = A4
        # Dark background
        c.setFillColor(DARK)
        c.rect(0, 0, w, h, fill=1, stroke=0)
        # Gold accent top
        c.setFillColor(GOLD)
        c.rect(0, h-8, w, 8, fill=1, stroke=0)
        # Subtle grid pattern
        c.setStrokeColor(colors.HexColor("#1E2028"))
        c.setLineWidth(0.4)
        for x in range(0, int(w)+20, 30):
            c.line(x, 0, x, h)
        for y in range(0, int(h)+20, 30):
            c.line(0, y, w, y)
        # Gold gradient block
        c.setFillColor(colors.HexColor("#1A1D24"))
        c.roundRect(40, h/2-80, w-80, 160, 12, fill=1, stroke=0)
        c.setStrokeColor(GOLD)
        c.setLineWidth(1.5)
        c.roundRect(40, h/2-80, w-80, 160, 12, fill=0, stroke=1)
        # Title
        c.setFillColor(GOLD)
        c.setFont("Helvetica-Bold", 40)
        c.drawCentredString(w/2, h/2+40, "HRM PORTAL")
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(w/2, h/2+10, "HR USER GUIDE")
        c.setFillColor(GOLD_LIGHT)
        c.setFont("Helvetica-Oblique", 12)
        c.drawCentredString(w/2, h/2-15, "Complete Reference for HR Administrators, Managers & Staff")
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 9)
        c.drawCentredString(w/2, h/2-45, "Navigate every module · Manage goals & KPIs · Configure payroll & compliance")
        # Bottom info
        c.setFillColor(colors.HexColor("#333640"))
        c.roundRect(40, 60, w-80, 45, 8, fill=1, stroke=0)
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 9)
        c.drawString(60, 90, "Audience: HR Admins · Managers · Staff")
        c.drawString(60, 75, "Covers: All Portal Modules · KPI Automation · Payroll · Recruitment · Compliance")
        c.setFillColor(GOLD)
        c.drawRightString(w-60, 82, "hrm-portal.internal")


# ─── BUILD DOCUMENT ──────────────────────────────────────────────────────────
def build():
    out = "hrm-portal/HRM_Portal_HR_Guide.pdf"
    doc = SimpleDocTemplate(
        out,
        pagesize=A4,
        leftMargin=1.6*cm, rightMargin=1.6*cm,
        topMargin=1.8*cm, bottomMargin=1.8*cm,
        title="HRM Portal HR Guide",
        author="HR Department",
    )

    story = []

    # ── COVER ────────────────────────────────────────────────────────────────
    story.append(CoverPage())
    story.append(PageBreak())

    # ── TABLE OF CONTENTS ────────────────────────────────────────────────────
    story.append(Paragraph("Table of Contents", S["ChapterTitle"]))
    story.append(hr(GOLD, 1.5))
    story.append(sp(4))

    toc = [
        ("1", "Getting Started & Portal Overview",           ""),
        ("",  "— Portal architecture · Login · Dashboard",   ""),
        ("2", "Portal Navigation & Sidebar Guide",            ""),
        ("",  "— Every sidebar section explained",           ""),
        ("3", "User Management & Roles",                      ""),
        ("",  "— Roles · Inviting users · Permissions table",""),
        ("4", "Recruitment & ATS Pipeline",                   ""),
        ("",  "— Jobs · Applications · Pipeline · Offers",   ""),
        ("5", "People & Organisation",                        ""),
        ("",  "— Employees · Org Chart · Departments",       ""),
        ("6", "Time & Attendance",                            ""),
        ("",  "— Clock-in · Timesheets · Shift Scheduling",  ""),
        ("7", "Leave Management",                             ""),
        ("",  "— Policies · Requests · Approval workflow",   ""),
        ("8", "Performance & KPI Management",                 ""),
        ("",  "— Goals & OKRs · KPI Library · Auto-grading", ""),
        ("9", "Payroll, Compensation & Benefits",             ""),
        ("",  "— Payroll runs · Payslips · Bonuses",         ""),
        ("10","Engagement, Culture & Communications",         ""),
        ("",  "— Announcements · Recognition · Surveys",     ""),
        ("11","Documents, Contracts & Compliance",            ""),
        ("",  "— Contract Kitchen · HR Letters · Grievances",""),
        ("12","Onboarding, Probation & Offboarding",          ""),
        ("",  "— Checklists · Probation tracking · Exit",    ""),
        ("13","Reports & Audit Logs",                         ""),
        ("14","Troubleshooting & Quick Reference",            ""),
    ]
    for (num, title, _) in toc:
        if num:
            story.append(Paragraph(f"<b>{num}.</b> {title}", S["TOC_H1"]))
        else:
            story.append(Paragraph(title, S["TOC_H2"]))
        story.append(sp(2))

    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # CHAPTER 1 — GETTING STARTED
    # ════════════════════════════════════════════════════════════════════════
    story.append(ChapterHeader("1", "Getting Started & Portal Overview",
                               "Login, dashboard orientation, and portal architecture"))
    story.append(sp(10))

    story.append(para(
        "The HRM Portal is your organisation's single platform for every HR function — from hiring "
        "and onboarding to payroll and performance management. This guide walks through every "
        "module so you can operate the portal confidently from day one."
    ))
    story.append(sp(6))

    story.append(Paragraph("1.1  Logging In", S["SectionTitle"]))
    story.append(para("Open the portal URL in your browser. Enter your registered email and password."))
    for i, t in enumerate([
        "Navigate to your organisation's portal URL.",
        "Enter your email address and password.",
        "Click <b>Sign In</b>. If this is your first login, use the temporary password from your invite email and change it immediately.",
        "If you have forgotten your password, click <b>Forgot Password</b> on the login screen.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(4))

    story.append(note("First-time users must change their temporary password before accessing the portal."))
    story.append(sp(8))

    story.append(Paragraph("1.2  Portal Architecture", S["SectionTitle"]))
    story.append(para(
        "The diagram below illustrates how the three user roles connect to portal modules, "
        "which in turn read from and write to the underlying data and integration layer."
    ))
    story.append(sp(6))
    story.append(PortalArchDiagram())
    story.append(Paragraph("Figure 1.1 — HRM Portal system overview", S["Caption"]))
    story.append(sp(8))

    story.append(Paragraph("1.3  Dashboard at a Glance", S["SectionTitle"]))
    story.append(para(
        "After login you land on the <b>HR Overview</b> dashboard. The dashboard shows KPI summary "
        "cards (total headcount, average performance score, pending leave requests), quick-link "
        "buttons to Goals, Staff, and Reports, and a notification bell in the top-right for "
        "pending actions."
    ))
    story.append(sp(4))
    story.append(bullet("<b>KPI cards</b> — click any card to drill into the underlying report."))
    story.append(bullet("<b>Quick links</b> — jump directly to Goals & OKRs or the Staff directory."))
    story.append(bullet("<b>Notification bell</b> — shows pending leave approvals, tasks, and system alerts."))
    story.append(bullet("<b>Theme toggle</b> — switch between dark and light mode (top-right corner)."))
    story.append(sp(6))

    story.append(Paragraph("1.4  User Roles Summary", S["SectionTitle"]))
    story.append(para("Three primary roles govern what each user can see and do:"))
    story.append(sp(4))
    story.append(role_table())
    story.append(sp(8))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # CHAPTER 2 — SIDEBAR NAVIGATION
    # ════════════════════════════════════════════════════════════════════════
    story.append(ChapterHeader("2", "Portal Navigation & Sidebar Guide",
                               "A complete map of every sidebar item visible to HR Admins"))
    story.append(sp(10))
    story.append(para(
        "The sidebar is your primary navigation tool. HR Admins see the full sidebar; Managers and "
        "Staff see a condensed version. The diagram below groups all sidebar items by section."
    ))
    story.append(sp(8))
    story.append(SidebarMapDiagram())
    story.append(Paragraph("Figure 2.1 — Sidebar section map (HR Admin view)", S["Caption"]))
    story.append(sp(10))

    sections_desc = [
        ("Overview", [
            ("HR Overview", "Main dashboard: KPI cards, quick links, and headcount summary."),
            ("Task Manager", "Create and assign HR tasks; mark complete; filter by assignee."),
        ]),
        ("Recruitment", [
            ("Jobs", "Post job adverts, set hiring manager, publish/close roles."),
            ("Job Requisitions", "Approve or reject headcount requisition requests."),
            ("Applications", "Review incoming applications; shortlist or reject candidates."),
            ("ATS Pipeline", "Visual kanban board — click a card to move candidates between stages."),
            ("Interviews", "Schedule interviews; send calendar invites; reschedule."),
            ("Offers", "Create and send offer letters; mark offers as accepted."),
            ("Talent Pool", "Store promising candidates for future openings."),
        ]),
        ("People & Org", [
            ("Employees", "Full staff directory: invite, edit, deactivate, export CSV."),
            ("Bio Data Collection", "Request and download employee bio data forms."),
            ("Guarantor Forms", "Manage guarantor submissions and verification."),
            ("Org Chart", "Visual reporting-line chart; export for presentations."),
            ("Departments", "Add and manage departments; assign department heads."),
            ("Diversity & Inclusion", "Run D&I surveys and view summary metrics."),
        ]),
        ("Time & Attendance", [
            ("Attendance", "View clock-in/out records; adjust entries; approve missing punches."),
            ("Timesheets", "Submit and approve weekly/monthly timesheets."),
            ("Timesheet Approvals", "Bulk approve or reject pending timesheet submissions."),
            ("Shift Scheduling", "Create shifts and publish rosters; manage shift swaps."),
            ("Calendar", "HR-wide event calendar; create and track HR events."),
            ("Holidays", "Define public holidays and company blackout dates."),
        ]),
        ("Leave", [
            ("Leave Requests", "Review pending requests; approve, reject, or bulk-approve."),
            ("Leave Balances", "View and manually adjust individual leave balances."),
            ("Leave Policies", "Create accrual policies and assign to employee groups."),
            ("Leave Accrual", "Configure and trigger automated balance accrual runs."),
        ]),
        ("Performance", [
            ("Performance", "High-level performance dashboards; filter by team or period."),
            ("Goals & OKRs", "Create, assign, and track goals; trigger KPI sync."),
            ("Improvement Plans", "Create and assign performance improvement plans (PIPs)."),
            ("360° Peer Reviews", "Manage multi-rater peer review cycles."),
            ("Skills Matrix", "View competency gaps; assign training."),
            ("Succession Planning", "Nominate successors and track readiness."),
        ]),
        ("Learning & Growth", [
            ("Training", "Create training sessions; enroll staff; track completion."),
            ("Onboarding", "Build and assign onboarding checklists for new hires."),
            ("Probation Tracking", "Start, monitor, and complete probation periods."),
        ]),
        ("Compensation & Benefits", [
            ("Payroll", "Run payroll; approve; export payslips."),
            ("Compensation Bands", "Define and edit salary bands."),
            ("Bonuses & Incentives", "Create bonus cycles; disburse to eligible staff."),
            ("Benefits", "Add and assign employee benefits packages."),
            ("Expenses", "Approve or reject expense claims."),
            ("Tax Configuration", "Edit tax rules and apply to payroll runs."),
        ]),
        ("Engagement & Culture", [
            ("Announcements", "Post, pin, and archive company-wide announcements."),
            ("Recognition", "Give and view peer recognition kudos."),
            ("Surveys", "Create, send, and analyse staff engagement surveys."),
            ("Remote Work", "Manage WFH requests and policies."),
            ("Policy Library", "Upload, share, and acknowledge HR policy documents."),
            ("Internal Job Board", "Post internal vacancies; allow self-application."),
        ]),
        ("Documents & Compliance", [
            ("Documents", "Central document vault: upload, download, set permissions."),
            ("⚖️ Contract Kitchen", "Draft and manage employment contracts; send for e-signature."),
            ("HR Letters", "Generate appointment, offer, and warning letters."),
            ("Work Permits", "Track permit documents and expiry dates."),
            ("Requests", "Manage general HR service requests from staff."),
            ("Grievances", "Open and track formal grievance cases."),
            ("Disciplinary Records", "Log disciplinary incidents and attach evidence."),
            ("Assets", "Assign and track company asset returns."),
        ]),
        ("Administration", [
            ("Reports", "Run scheduled or on-demand HR reports; export as PDF or Excel."),
            ("Exit & Offboarding", "Initiate and track the offboarding checklist."),
            ("Exit Interviews", "Schedule and record exit interview notes."),
            ("Users", "Manage system user accounts; change roles; deactivate."),
            ("Audit Logs", "View full system activity log; filter and export."),
            ("Settings", "Configure system-wide HR settings."),
            ("My Profile", "Update personal info, change password, upload avatar."),
        ]),
    ]

    for sec_name, items in sections_desc:
        story.append(subhead(f"Section: {sec_name}"))
        rows = [[Paragraph(f"<b>{item}</b>", S["TableCellBold"]),
                 Paragraph(desc, S["TableCell"])] for item, desc in items]
        t = Table(rows, colWidths=[120, None])
        t.setStyle(TableStyle([
            ("ROWBACKGROUNDS", (0,0), (-1,-1), [WHITE, LIGHT_BG]),
            ("GRID", (0,0), (-1,-1), 0.3, BORDER),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING", (0,0), (-1,-1), 8),
            ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ]))
        story.append(t)
        story.append(sp(8))

    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # CHAPTER 3 — USER MANAGEMENT
    # ════════════════════════════════════════════════════════════════════════
    story.append(ChapterHeader("3", "User Management & Roles",
                               "Invite users, assign roles, and manage permissions"))
    story.append(sp(10))

    story.append(Paragraph("3.1  Inviting a New User", S["SectionTitle"]))
    for i, t in enumerate([
        "Navigate to <b>People & Org → Employees</b> to add new staff.",
        "Click <b>Add New Staff Member</b> (or `Invite`) → fill Full Name, Email, Department, Roles → set a default password and confirm.",
        "Click <b>Create Staff Account</b> to create the account (HR sets the initial password).",
        "The user must change their password on first login.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(6))

    story.append(Paragraph("3.2  Editing a User Profile", S["SectionTitle"]))
    for i, t in enumerate([
        "Go to <b>People & Org → Employees</b>.",
        "Search for the staff member and click their name.",
        "Click <b>Edit Profile</b> to update: job title, department, line manager, phone number, and employment type.",
        "Click <b>Save</b>.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(6))

    story.append(Paragraph("3.3  Deactivating a User", S["SectionTitle"]))
    story.append(para(
        "Deactivation prevents portal access without deleting records. Only deactivate accounts for "
        "leavers — not for role changes or temporary leave."
    ))
    for i, t in enumerate([
        "Open the staff profile via <b>Employees</b>.",
        "Click <b>Edit Profile</b>.",
        "Click <b>Deactivate Account</b> and confirm.",
        "The account is locked immediately. Historical records are preserved.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(6))

    story.append(Paragraph("3.4  Permission Matrix", S["SectionTitle"]))
    story.append(para("The table below summarises key actions by role:"))
    story.append(sp(4))
    story.append(permissions_table())
    story.append(sp(8))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # CHAPTER 4 — RECRUITMENT
    # ════════════════════════════════════════════════════════════════════════
    story.append(ChapterHeader("4", "Recruitment & ATS Pipeline",
                               "Post jobs, track applicants, schedule interviews, and issue offers"))
    story.append(sp(10))

    story.append(Paragraph("4.1  Recruitment Funnel", S["SectionTitle"]))
    story.append(RecruitmentPipeline())
    story.append(Paragraph("Figure 4.1 — Typical ATS candidate funnel", S["Caption"]))
    story.append(sp(8))

    story.append(Paragraph("4.2  Posting a Job", S["SectionTitle"]))
    for i, t in enumerate([
        "Go to <b>Recruitment → Jobs → New Job</b>.",
        "Enter: Job Title, Department, Hiring Manager, Location, and Job Description.",
        "Attach any required documents (e.g., job spec PDF).",
        "Click <b>Publish</b> to make the role live. It will appear on the Internal Job Board and any integrated external channel.",
        "Use <b>Close Job</b> once hiring is complete.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(6))

    story.append(Paragraph("4.3  Managing Applications", S["SectionTitle"]))
    for i, t in enumerate([
        "Open <b>Recruitment → Applications</b>.",
        "Filter by job, keyword, or stage.",
        "Click a candidate to open their profile.",
        "Choose <b>Shortlist</b> to advance the candidate or <b>Reject</b> to close their application (an automated email is sent).",
        "To schedule an interview: click <b>Schedule Interview</b>, pick an interviewer and time slot, then click <b>Send Invite</b>.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(6))

    story.append(Paragraph("4.4  ATS Pipeline (Kanban Board)", S["SectionTitle"]))
    story.append(para(
        "The ATS Pipeline provides a visual kanban board where each column represents a hiring stage. "
        "HR and hiring managers can drag candidate cards between stages in real time."
    ))
    story.append(bullet("Stages: <b>Applied → Screened → Interview → Offer → Hired</b>"))
    story.append(bullet("Click a card to <b>Add Note</b> or <b>Email Candidate</b>."))
    story.append(bullet("Stage changes are logged in the candidate's activity timeline."))
    story.append(sp(6))

    story.append(Paragraph("4.5  Making an Offer", S["SectionTitle"]))
    for i, t in enumerate([
        "Go to <b>Recruitment → Offers → Create Offer</b>.",
        "Select the candidate and position.",
        "Fill in the offer details (salary, start date, probation period).",
        "Click <b>Send Offer</b>. The candidate receives the offer letter for review.",
        "Once the candidate accepts, click <b>Mark Accepted</b> — the system triggers the onboarding workflow.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(8))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # CHAPTER 5 — PEOPLE & ORG
    # ════════════════════════════════════════════════════════════════════════
    story.append(ChapterHeader("5", "People & Organisation",
                               "Staff directory, org chart, departments, and bio data"))
    story.append(sp(10))

    story.append(Paragraph("5.1  Employees Module", S["SectionTitle"]))
    story.append(para(
        "The Employees module is the central staff registry. Every person in the organisation "
        "has a profile here, regardless of their system role."
    ))
    story.append(bullet("<b>Invite</b> — adds a new user account and sends a welcome email."))
    story.append(bullet("<b>Edit Profile</b> — update title, department, manager, contact details."))
    story.append(bullet("<b>Deactivate</b> — locks portal access for leavers without deleting records."))
    story.append(bullet("<b>Export CSV</b> — downloads the full staff list for reporting or external HR systems."))
    story.append(sp(6))

    story.append(Paragraph("5.2  Org Chart", S["SectionTitle"]))
    story.append(para(
        "The Org Chart page renders a live visual of the organisation's reporting hierarchy. "
        "Use it to verify that all line-manager relationships are correctly set before running "
        "performance reviews or payroll. Click <b>Export</b> to download a PNG for presentations."
    ))
    story.append(sp(4))
    story.append(note("If a staff member appears without a manager, edit their profile and set the Line Manager field."))
    story.append(sp(6))

    story.append(Paragraph("5.3  Departments", S["SectionTitle"]))
    for i, t in enumerate([
        "Go to <b>People & Org → Departments → Add Department</b>.",
        "Enter department name, department head, and a brief description.",
        "Click <b>Save</b>. The new department is now available in all dropdowns (goals, leave policies, reports).",
    ], 1):
        story.append(step(i, t))
    story.append(sp(6))

    story.append(Paragraph("5.4  Bio Data Collection", S["SectionTitle"]))
    story.append(para(
        "HR can request employees to fill in a structured bio data form covering personal details, "
        "qualifications, next of kin, and bank information. The form link is sent via email."
    ))
    story.append(bullet("Go to <b>Bio Data Collection → Request Form</b> and select the staff member(s)."))
    story.append(bullet("The employee receives a secure, tokenised link to complete the form."))
    story.append(bullet("Submitted forms appear in <b>Bio Data Collection</b> for HR review and download."))
    story.append(sp(6))

    story.append(Paragraph("5.5  Guarantor Forms", S["SectionTitle"]))
    story.append(para(
        "For roles requiring a guarantor, HR uses <b>Guarantor Forms</b> to request, verify, and "
        "store completed guarantor submissions. Click <b>Request Guarantor</b>, select the staff member, "
        "and the guarantor receives a secure form link. Once submitted, HR clicks <b>Verify</b> to "
        "confirm the guarantor's details."
    ))
    story.append(sp(8))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # CHAPTER 6 — TIME & ATTENDANCE
    # ════════════════════════════════════════════════════════════════════════
    story.append(ChapterHeader("6", "Time & Attendance",
                               "Clock-in records, timesheets, shift scheduling, and holidays"))
    story.append(sp(10))

    story.append(Paragraph("6.1  Attendance Records", S["SectionTitle"]))
    story.append(para(
        "The Attendance page shows every clock-in and clock-out event. Events are captured "
        "automatically when staff use the mobile or web attendance widget."
    ))
    story.append(bullet("<b>Adjust Entry</b> — correct a wrong clock time (e.g., forgotten clock-out)."))
    story.append(bullet("<b>Approve Missing Punches</b> — authorise records with no clock-out."))
    story.append(bullet("<b>Export</b> — download attendance data for payroll verification."))
    story.append(sp(6))

    story.append(Paragraph("6.2  Timesheets", S["SectionTitle"]))
    story.append(para(
        "Staff submit timesheets weekly or monthly (depending on policy). Managers and HR "
        "review submissions before approving."
    ))
    for i, t in enumerate([
        "Open <b>Time & Attendance → Timesheets</b>.",
        "Filter by period and employee.",
        "Open a timesheet to review hours by day.",
        "Click <b>Approve</b> to confirm, or <b>Request Changes</b> to send back with a comment.",
        "Approved timesheets feed into payroll calculation.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(4))
    story.append(note("Bulk approve: use Timesheet Approvals under the same section to process multiple at once."))
    story.append(sp(6))

    story.append(Paragraph("6.3  Shift Scheduling", S["SectionTitle"]))
    for i, t in enumerate([
        "Go to <b>Shift Scheduling → Create Shift</b>.",
        "Set owner (employee or team), start time, end time, and repeat rules (daily/weekly).",
        "Click <b>Publish Schedule</b> to notify affected staff.",
        "Staff can request a <b>Swap Shift</b>; the request is routed to the manager for approval.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(6))

    story.append(Paragraph("6.4  Holidays Manager", S["SectionTitle"]))
    story.append(para(
        "Define public holidays and company blackout dates here. These dates are automatically "
        "excluded from leave balance calculations and shift schedules."
    ))
    story.append(bullet("Go to <b>Holidays → Add Holiday</b> and enter the name, date, and whether it is a recurring annual holiday."))
    story.append(sp(8))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # CHAPTER 7 — LEAVE MANAGEMENT
    # ════════════════════════════════════════════════════════════════════════
    story.append(ChapterHeader("7", "Leave Management",
                               "Policies, requests, approvals, balances, and accrual"))
    story.append(sp(10))

    story.append(Paragraph("7.1  Leave Approval Workflow", S["SectionTitle"]))
    story.append(LeaveFlowDiagram())
    story.append(Paragraph("Figure 7.1 — Leave request approval workflow", S["Caption"]))
    story.append(sp(10))

    story.append(Paragraph("7.2  Approving a Leave Request", S["SectionTitle"]))
    for i, t in enumerate([
        "Open <b>Leave → Leave Requests</b>.",
        "Filter by status: <b>Pending</b>.",
        "Click a request to view details, attachments, and the employee's remaining balance.",
        "Click <b>Approve</b> or <b>Reject</b>. Add an optional comment for the employee.",
        "The employee is notified immediately by email and their balance is updated.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(4))
    story.append(note("Use Bulk Approve to process multiple pending requests simultaneously — use cautiously."))
    story.append(sp(6))

    story.append(Paragraph("7.3  Managing Leave Balances", S["SectionTitle"]))
    story.append(bullet("Go to <b>Leave → Leave Balances</b> and search for the employee."))
    story.append(bullet("Click <b>Adjust Balance</b> to manually correct accrual errors."))
    story.append(bullet("Always add a note explaining the adjustment for audit purposes."))
    story.append(sp(6))

    story.append(Paragraph("7.4  Leave Policies", S["SectionTitle"]))
    story.append(para(
        "Leave policies define how many days each leave type accrues per period and who is eligible."
    ))
    for i, t in enumerate([
        "Go to <b>Leave → Leave Policies → Create Policy</b>.",
        "Name the policy (e.g., 'Annual Leave — Full Time'), set leave type, accrual rate, carry-over rules, and maximum balance.",
        "Click <b>Assign</b> to link the policy to one or more employee groups.",
        "Edit existing policies using the <b>Edit</b> button; changes take effect from the next accrual run.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(6))

    story.append(Paragraph("7.5  Leave Accrual", S["SectionTitle"]))
    story.append(para(
        "The <b>Leave Accrual</b> page lets HR configure and trigger accrual runs. Accrual can be "
        "set to run automatically on a schedule or triggered manually."
    ))
    story.append(bullet("Click <b>Edit Accrual</b> to change the accrual schedule."))
    story.append(bullet("Click <b>Run Accrual</b> to immediately process balances for all eligible staff."))
    story.append(sp(8))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # CHAPTER 8 — PERFORMANCE & KPIs
    # ════════════════════════════════════════════════════════════════════════
    story.append(ChapterHeader("8", "Performance & KPI Management",
                               "Goals & OKRs, KPI Library, automated grading, and sync engine"))
    story.append(sp(10))

    story.append(Paragraph("8.1  Overview", S["SectionTitle"]))
    story.append(para(
        "The Performance module supports goal-setting, KPI tracking, peer reviews, improvement plans, "
        "and succession planning. The most-used section is <b>Goals & OKRs</b>, where HR creates goals, "
        "assigns them to individuals or departments, and monitors achievement automatically or manually."
    ))
    story.append(sp(6))

    story.append(Paragraph("8.2  KPI Library — Creating Templates", S["SectionTitle"]))
    story.append(para(
        "The KPI Library holds reusable measurement templates. Before creating a goal, at least one "
        "KPI template must exist."
    ))
    for i, t in enumerate([
        "Go to <b>Performance → Goals & OKRs</b> and click <b>Manage KPI Library</b>.",
        "Click <b>+ Define New KPI</b>.",
        "Enter: <b>KPI Name</b> (e.g., 'Monthly Sales Revenue'), <b>Target Department</b>, <b>Measurement Source</b> (see table below), <b>Default Unit</b> (e.g., NGN, deals, %), and a <b>Description</b>.",
        "Toggle <b>Active</b> to ON.",
        "Click <b>Save</b>.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(6))

    story.append(Paragraph("8.3  Measurement Sources Reference", S["SectionTitle"]))
    story.append(kpi_sources_table())
    story.append(sp(8))

    story.append(Paragraph("8.4  Creating and Assigning a Goal", S["SectionTitle"]))
    for i, t in enumerate([
        "Open <b>Goals & OKRs → Create & Activate Goal</b>.",
        "Choose assignment type: <b>Staff Member</b> or <b>Department</b>.",
        "Select a KPI template from the library (recommended) or type a custom KPI name.",
        "Set <b>Monthly Target</b>, <b>Unit</b>, and <b>Performance Period</b> (select the month).",
        "Set <b>Publication Status</b> to <b>Published</b> so the staff member can see their goal.",
        "Click <b>Create & Activate Goal</b>. The goal appears in the list with a progress bar.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(4))
    story.append(note("If you select an automated template, the system calculates actual values during the next sync."))
    story.append(sp(8))

    story.append(Paragraph("8.5  Automated KPI Grading Flow", S["SectionTitle"]))
    story.append(KPIFlowDiagram())
    story.append(Paragraph("Figure 8.1 — KPI grading decision flow (automated vs manual)", S["Caption"]))
    story.append(sp(10))

    story.append(Paragraph("8.6  Triggering the Sync", S["SectionTitle"]))
    story.append(para(
        "Automated KPIs are refreshed nightly by a backend scheduler. To request an immediate "
        "refresh during testing or after a data change:"
    ))
    for i, t in enumerate([
        "Open <b>Performance → Goals & OKRs</b>.",
        "Click the <b>🔄 Sync Performance</b> button (top-right of the Goals list).",
        "Wait 2–10 seconds, then refresh the page.",
        "Verify that <b>achievement_pct</b> has updated and <b>last_synced_at</b> shows the current time.",
        "Check <b>achievement_status</b>: Achieved / On Track / At Risk / Behind.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(6))

    story.append(Paragraph("8.7  Updating Manual KPIs", S["SectionTitle"]))
    story.append(para(
        "For goals using the <b>manual</b> measurement source, the manager or HR must enter the "
        "actual value themselves."
    ))
    for i, t in enumerate([
        "Open the goal from the Goals & OKRs list.",
        "Click <b>Update Progress</b> (or <b>Edit</b>).",
        "Enter the actual value in the <b>Actual</b> field.",
        "Click <b>Save</b>. The system recalculates achievement_pct immediately.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(6))

    story.append(Paragraph("8.8  Sales Rep Mapping (Required for Revenue KPIs)", S["SectionTitle"]))
    story.append(para(
        "Sales KPIs (sales_revenue, sales_deals_closed, sales_collection_rate) resolve "
        "amounts by looking up the staff member's <b>sales_rep_id</b> in the database. If this "
        "link is missing, revenue KPIs may remain 0 even after sync."
    ))
    story.append(bullet("Confirm with Sales Ops or your development team that each HR staff account is mapped to the correct <b>sales_rep_id</b> record in the backend system."))
    story.append(bullet("This mapping is not configured in the HR portal UI itself; it must exist in the underlying sales/reps data model.") )
    story.append(bullet("Once the mapping exists, click <b>🔄 Sync Performance</b> again and verify KPI values update."))
    story.append(sp(6))

    story.append(Paragraph("8.9  360° Peer Reviews", S["SectionTitle"]))
    for i, t in enumerate([
        "Go to <b>Performance → 360° Peer Reviews → Create Review</b>.",
        "Select the reviewee and the review period.",
        "Click <b>Invite Reviewers</b> and add peers, direct reports, and the line manager.",
        "Choose whether to enable <b>Anonymous responses</b>; reviewer identities are hidden in the final results when this option is selected.",
        "Reviewers receive email invitations to complete the questionnaire.",
        "Once all reviews are submitted, click <b>Publish Results</b> to share with the reviewee.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(8))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # CHAPTER 9 — PAYROLL
    # ════════════════════════════════════════════════════════════════════════
    story.append(ChapterHeader("9", "Payroll, Compensation & Benefits",
                               "Run payroll, issue payslips, configure bonuses, benefits, and tax"))
    story.append(sp(10))

    story.append(Paragraph("9.1  Running Payroll", S["SectionTitle"]))
    for i, t in enumerate([
        "Go to <b>Compensation & Benefits → Payroll</b>.",
        "Click <b>Run Payroll</b>.",
        "Verify the pay period and review the total payroll summary.",
        "Click <b>Approve & Run</b> to finalise.",
        "Use <b>Export Payslips</b> to download payslip PDFs for distribution.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(4))
    story.append(note("Payroll pulls in approved timesheets, bonuses, and tax rules automatically. Verify all inputs before running."))
    story.append(sp(6))

    story.append(Paragraph("9.2  Payslip Breakdown", S["SectionTitle"]))
    story.append(para(
        "Each payslip shows: basic salary, allowances, bonuses/commissions, tax deductions, pension "
        "contributions, and net pay. Staff can view their own payslips under <b>My Payslip</b>."
    ))
    story.append(sp(6))

    story.append(Paragraph("9.3  Compensation Bands", S["SectionTitle"]))
    story.append(para(
        "Compensation Bands define salary ranges for each grade or role. HR uses these to ensure "
        "new hires and promotions fall within approved ranges."
    ))
    story.append(bullet("Go to <b>Compensation Bands → Edit Band</b> to update min/max salaries."))
    story.append(bullet("Click <b>Export</b> to generate a compensation band report for senior management."))
    story.append(sp(6))

    story.append(Paragraph("9.4  Bonuses & Incentives", S["SectionTitle"]))
    for i, t in enumerate([
        "Go to <b>Bonuses & Incentives → Create Bonus</b>.",
        "Select the bonus type (performance, referral, discretionary), eligible staff, and amounts.",
        "Click <b>Disburse</b>. The bonus is added to the next payroll run.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(6))

    story.append(Paragraph("9.5  Benefits Management", S["SectionTitle"]))
    story.append(para(
        "Add benefit packages (health insurance, pension, meal vouchers) and assign them to "
        "individual staff or entire departments via <b>Benefits → Add Benefit → Assign to Staff</b>."
    ))
    story.append(sp(6))

    story.append(Paragraph("9.6  Tax Configuration", S["SectionTitle"]))
    story.append(para(
        "Tax rules are managed under <b>Tax Configuration</b>. After editing tax bands or rates, "
        "click <b>Apply to Payroll</b> to ensure the next payroll run uses the updated rules."
    ))
    story.append(sp(8))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # CHAPTER 10 — ENGAGEMENT & CULTURE
    # ════════════════════════════════════════════════════════════════════════
    story.append(ChapterHeader("10", "Engagement, Culture & Communications",
                               "Announcements, recognition, surveys, remote work, and policy library"))
    story.append(sp(10))

    story.append(Paragraph("10.1  Announcements", S["SectionTitle"]))
    for i, t in enumerate([
        "Go to <b>Engagement & Culture → Announcements → New Announcement</b>.",
        "Enter a title, body text, and select the target audience (all staff, a department, or specific roles).",
        "Click <b>Publish</b>. The announcement appears on all targeted staff dashboards immediately.",
        "Use <b>Pin</b> to keep important notices at the top of the feed; use <b>Archive</b> to remove outdated ones.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(6))

    story.append(Paragraph("10.2  Recognition Wall", S["SectionTitle"]))
    story.append(para(
        "The Recognition Wall is a company-wide kudos feed. HR and managers can highlight "
        "exceptional contributions publicly."
    ))
    story.append(bullet("Click <b>Give Recognition</b>, select the staff member, choose a badge category, and write a note."))
    story.append(bullet("Recognitions appear in the feed visible to all staff, boosting engagement."))
    story.append(sp(6))

    story.append(Paragraph("10.3  Surveys", S["SectionTitle"]))
    for i, t in enumerate([
        "Go to <b>Surveys → Create Survey</b>.",
        "Add questions (multiple choice, rating scale, or open text).",
        "Choose recipients (all staff, a department, or specific individuals).",
        "Click <b>Send</b>. Staff receive a survey link via email or in-app notification.",
        "View <b>Results</b> once responses are collected — charts are generated automatically.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(6))

    story.append(Paragraph("10.4  Remote Work Requests", S["SectionTitle"]))
    story.append(para(
        "Staff submit WFH requests via <b>Remote Work → Request WFH</b>. "
        "HR or managers approve via the same module. HR can toggle to the HR view to see all requests across the organisation."
    ))
    story.append(sp(6))

    story.append(Paragraph("10.5  Policy Library", S["SectionTitle"]))
    story.append(para(
        "Upload HR policy documents (employee handbook, code of conduct, data policy) to the "
        "Policy Library. Staff must <b>Acknowledge</b> reading key documents — acknowledgement "
        "records are stored for compliance."
    ))
    story.append(sp(8))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # CHAPTER 11 — DOCUMENTS & COMPLIANCE
    # ════════════════════════════════════════════════════════════════════════
    story.append(ChapterHeader("11", "Documents, Contracts & Compliance",
                               "Document vault, Contract Kitchen, HR letters, grievances, and disciplinary"))
    story.append(sp(10))

    story.append(Paragraph("11.1  Documents Vault", S["SectionTitle"]))
    story.append(para(
        "The Documents Vault is a central repository for all HR-related files. Access is "
        "controlled by permissions set per document."
    ))
    story.append(bullet("<b>Upload</b> — add a new document and set access permissions (HR only, manager, all staff)."))
    story.append(bullet("<b>Download</b> — retrieve any document you have permission to view."))
    story.append(bullet("<b>Set Permissions</b> — restrict or widen access at any time."))
    story.append(sp(6))

    story.append(Paragraph("11.2  Contract Kitchen", S["SectionTitle"]))
    story.append(para(
        "Contract Kitchen is the portal's contract management system. It supports creation, "
        "digital signing, and archiving of employment contracts."
    ))
    for i, t in enumerate([
        "Go to <b>Documents & Compliance → ⚖️ Contract Kitchen → New Contract</b>.",
        "Select a template (e.g., Full-Time Employment Agreement) and populate staff-specific details.",
        "Click <b>Send for Signature</b>. The staff member receives a secure signing link.",
        "Once signed, the contract status updates to <b>Executed</b> and is stored in the vault.",
        "Use <b>Archive</b> for terminated or superseded contracts.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(6))

    story.append(Paragraph("11.3  HR Letters", S["SectionTitle"]))
    story.append(para(
        "Generate standard letters (appointment letters, promotion letters, query letters, "
        "warning notices) from pre-built templates."
    ))
    story.append(bullet("Go to <b>HR Letters → Create Letter</b>, choose a template, and fill in variables."))
    story.append(bullet("Click <b>Send</b> to email the letter or download as a PDF."))
    story.append(sp(6))

    story.append(Paragraph("11.4  Grievances & Disciplinary Records", S["SectionTitle"]))
    story.append(bullet("<b>Grievances:</b> Open a case from <b>Grievances → Open Case</b>, log details, update status as the case progresses, and choose anonymous submission if needed."))
    story.append(bullet("Anonymous grievances are handled confidentially; the system stores the case without tracing it back to the reporter when anonymity is selected."))
    story.append(bullet("<b>Disciplinary:</b> Record an incident via <b>Disciplinary Records → New Incident</b>, attach evidence (e.g., written warning), and track outcomes."))
    story.append(bullet("All records are time-stamped and audit-logged."))
    story.append(sp(6))

    story.append(Paragraph("11.5  Work Permits & Assets", S["SectionTitle"]))
    story.append(bullet("<b>Work Permits:</b> Upload permit documents; the system flags approaching expiry dates."))
    story.append(bullet("<b>Assets:</b> Assign company assets (laptop, phone) to staff; track return on offboarding."))
    story.append(sp(8))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # CHAPTER 12 — ONBOARDING & OFFBOARDING
    # ════════════════════════════════════════════════════════════════════════
    story.append(ChapterHeader("12", "Onboarding, Probation & Offboarding",
                               "New hire checklists, probation tracking, and exit management"))
    story.append(sp(10))

    story.append(Paragraph("12.1  Onboarding Flow", S["SectionTitle"]))
    story.append(OnboardingFlow())
    story.append(Paragraph("Figure 12.1 — New hire onboarding journey", S["Caption"]))
    story.append(sp(8))

    story.append(Paragraph("12.2  Creating an Onboarding Checklist", S["SectionTitle"]))
    for i, t in enumerate([
        "Go to <b>Learning & Growth → Onboarding → Create Checklist</b>.",
        "Add tasks: e.g., Sign Employment Contract, Complete ID Verification, IT Equipment Issued, Company Email Created, Meet Line Manager, Complete Probation Agreement.",
        "Assign the checklist to the new hire.",
        "Track completion from the Onboarding dashboard — incomplete tasks show as pending.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(6))

    story.append(Paragraph("12.3  Probation Tracking", S["SectionTitle"]))
    for i, t in enumerate([
        "Go to <b>Learning & Growth → Probation Tracking → Start Probation</b>.",
        "Select the employee and set the probation duration (typically 3–6 months).",
        "The system tracks days elapsed and sends reminders as the end date approaches.",
        "On completion, click <b>Complete</b> to confirm passing, or <b>Flag</b> to extend or escalate.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(6))

    story.append(Paragraph("12.4  Exit & Offboarding", S["SectionTitle"]))
    for i, t in enumerate([
        "Go to <b>Administration → Exit & Offboarding → Start Offboarding</b>.",
        "Select the leaving staff member and their last working day.",
        "The system generates an offboarding checklist: asset return, access revocation, payroll finalisation, exit survey.",
        "Schedule and record an <b>Exit Interview</b> via <b>Exit Interviews → Schedule</b>.",
        "Deactivate the user account after the last working day.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(8))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # CHAPTER 13 — REPORTS & AUDIT
    # ════════════════════════════════════════════════════════════════════════
    story.append(ChapterHeader("13", "Reports & Audit Logs",
                               "Scheduled reports, on-demand exports, and system audit trail"))
    story.append(sp(10))

    story.append(Paragraph("13.1  Running a Report", S["SectionTitle"]))
    for i, t in enumerate([
        "Go to <b>Administration → Reports</b>.",
        "Choose a report type (e.g., Headcount, Leave Summary, Performance Scores, Payroll Summary).",
        "Set the date range or period.",
        "Click <b>Run Report</b> to generate immediately, or <b>Schedule</b> to automate it (daily/weekly/monthly) and add recipient email addresses.",
        "Click <b>Export</b> to download as PDF or Excel.",
    ], 1):
        story.append(step(i, t))
    story.append(sp(6))

    story.append(Paragraph("13.2  Audit Logs", S["SectionTitle"]))
    story.append(para(
        "The Audit Logs page records every user action in the system — logins, record edits, "
        "approvals, and deletions. Logs cannot be deleted and are essential for compliance audits."
    ))
    story.append(bullet("<b>Filter</b> by user, action type, date range, or module."))
    story.append(bullet("<b>Export</b> the filtered log as CSV for external audit review."))
    story.append(sp(8))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # CHAPTER 14 — TROUBLESHOOTING
    # ════════════════════════════════════════════════════════════════════════
    story.append(ChapterHeader("14", "Troubleshooting & Quick Reference",
                               "Common issues, resolutions, and HR vs Developer responsibilities"))
    story.append(sp(10))

    story.append(Paragraph("14.1  Common Issues", S["SectionTitle"]))
    story.append(troubleshoot_table())
    story.append(sp(10))

    story.append(Paragraph("14.2  HR Actions vs Developer Actions", S["SectionTitle"]))
    headers = ["Action", "Who Does It"]
    rows = [
        ["Create KPI templates",                         "HR Admin (no code required)"],
        ["Create & assign goals",                        "HR Admin"],
        ["Link staff to sales rep records",              "HR Admin / Sales Ops"],
        ["Update manual KPI actuals",                    "Manager or HR Admin"],
        ["Trigger Sync Performance",                     "HR Admin"],
        ["Publish goals to staff",                       "HR Admin"],
        ["Run DB migrations (admins.sales_rep_id, etc.)", "Developer / DBA"],
        ["Deploy sync_goal_actuals engine",              "Developer"],
        ["Configure nightly scheduler",                  "Developer / DevOps"],
        ["Backfill marketing created_by column",         "Developer"],
        ["Add resolved_at to support_tickets",           "Developer"],
    ]
    story.append(make_table(headers, rows))
    story.append(sp(10))

    story.append(Paragraph("14.3  Department Alias Map", S["SectionTitle"]))
    story.append(para(
        "The portal maps several department name variants to canonical names when evaluating KPIs. "
        "Use the canonical name when creating departments to avoid mismatches."
    ))
    headers2 = ["Staff Department Name (variant)", "Canonical KPI Department Name"]
    rows2 = [
        ["Sales",              "Sales & Acquisitions"],
        ["Acquisitions",       "Sales & Acquisitions"],
        ["Sales and Acquisitions", "Sales & Acquisitions"],
        ["HR",                 "Human Resources"],
        ["H.R.",               "Human Resources"],
        ["Ops",                "Operations"],
        ["IT",                 "Information Technology"],
        ["Finance & Accounts", "Finance"],
        ["Accounts",           "Finance"],
    ]
    story.append(make_table(headers2, rows2))
    story.append(sp(10))

    story.append(Paragraph("14.4  Performance Score Calculation", S["SectionTitle"]))
    story.append(para(
        "The overall performance score is a weighted composite:"
    ))
    headers3 = ["Component", "Weight", "Source"]
    rows3 = [
        ["Goals Achievement (KPI Score)", "40%", "achievement_pct from staff_goals"],
        ["Quality of Work",               "20%", "Manager-entered quality score"],
        ["Manager Review",                "40%", "Manager review rating"],
    ]
    story.append(make_table(headers3, rows3))
    story.append(sp(6))
    story.append(note("Scores below 60 are flagged as 'At Risk' and may trigger an Improvement Plan."))
    story.append(sp(10))

    story.append(Paragraph("14.5  KPI Achievement Status Reference", S["SectionTitle"]))
    headers4 = ["Status",    "Condition",             "Action Recommended"]
    rows4 = [
        ["Achieved",  "achievement_pct ≥ 100%", "Celebrate; consider bonus eligibility"],
        ["On Track",  "75% ≤ pct < 100%",        "Monitor; check in at mid-month"],
        ["At Risk",   "50% ≤ pct < 75%",          "Manager coaching; review obstacles"],
        ["Behind",    "pct < 50%",                 "Escalate; consider PIP if persistent"],
    ]
    story.append(make_table(headers4, rows4))
    story.append(sp(8))

    story.append(Paragraph("14.6  Quick-Action Cheat Sheet", S["SectionTitle"]))
    headers5 = ["Task",                          "Navigation Path",                        "Button"]
    rows5 = [
        ["Invite a new employee",        "People & Org → Employees",                "Invite"],
        ["Approve leave",                "Leave → Leave Requests",                  "Approve / Bulk Approve"],
        ["Create a KPI template",        "Performance → Goals & OKRs → Manage KPI Library","+ Define New KPI"],
        ["Assign a goal",                "Performance → Goals & OKRs",              "Create & Activate Goal"],
        ["Trigger KPI sync",             "Performance → Goals & OKRs",              "🔄 Sync Performance"],
        ["Run payroll",                  "Compensation → Payroll",                  "Run Payroll"],
        ["Post announcement",            "Engagement → Announcements",              "New Announcement"],
        ["Create a contract",            "Documents → ⚖️ Contract Kitchen",         "New Contract"],
        ["View audit log",               "Administration → Audit Logs",             "Filter / Export"],
        ["Start offboarding",            "Administration → Exit & Offboarding",     "Start Offboarding"],
        ["Change user role",             "Administration → Users",                  "Change Role"],
    ]
    story.append(make_table(headers5, rows5))
    story.append(sp(12))

    story.append(hr(GOLD, 1.5))
    story.append(sp(6))
    story.append(para(
        "<i>This guide covers all modules available to HR Admins as of the current portal version. "
        "For questions about backend configuration or API integrations, contact your development team. "
        "For portal access issues, raise a ticket through Administration → Requests.</i>",
        "BodySmall"
    ))

    # ─── BUILD ────────────────────────────────────────────────────────────────
    doc.build(story, onFirstPage=lambda c, d: None, onLaterPages=make_header_footer)
    print(f"PDF written to {out}")


build()