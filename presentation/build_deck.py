#!/usr/bin/env python3
"""Build the editable Vietnamese Guarduty AI Ops presentation."""

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "presentation" / "guarduty-aiops.pptx"

SW, SH = 13.333, 7.5
COL = {
    "navy": "101B32",
    "navy2": "172848",
    "blue": "2F68D8",
    "teal": "19B7A2",
    "mint": "DFF7F1",
    "orange": "F28B43",
    "amber": "FFF0D9",
    "red": "D9534F",
    "ink": "1D2B43",
    "muted": "64748B",
    "line": "D9E2EE",
    "paper": "F5F8FC",
    "white": "FFFFFF",
    "slate": "EAF0F7",
    "green": "168363",
}


def rgb(value):
    return RGBColor.from_string(COL.get(value, value))


def shape(slide, kind, x, y, w, h, fill, line=None, radius=True):
    typ = MSO_SHAPE.ROUNDED_RECTANGLE if radius else kind
    obj = slide.shapes.add_shape(typ, Inches(x), Inches(y), Inches(w), Inches(h))
    obj.fill.solid()
    obj.fill.fore_color.rgb = rgb(fill)
    obj.line.fill.background() if line is None else None
    if line:
        obj.line.color.rgb = rgb(line)
        obj.line.width = Pt(1)
    return obj


def text(slide, value, x, y, w, h, size=16, color="ink", bold=False,
         align=PP_ALIGN.LEFT, valign=MSO_ANCHOR.TOP, font="Aptos",
         margin=0, italic=False):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Inches(margin)
    tf.margin_right = Inches(margin)
    tf.margin_top = Inches(margin)
    tf.margin_bottom = Inches(margin)
    tf.vertical_anchor = valign
    p = tf.paragraphs[0]
    p.alignment = align
    p.space_after = Pt(0)
    run = p.add_run()
    run.text = value
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = rgb(color)
    return box


def bullets(slide, items, x, y, w, h, size=15, color="ink", gap=8,
            bullet_color="teal"):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Inches(0)
    tf.margin_right = Inches(0)
    tf.margin_top = Inches(0)
    tf.margin_bottom = Inches(0)
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        p.level = 0
        r = p.add_run()
        r.text = "•  "
        r.font.name = "Aptos"
        r.font.size = Pt(size)
        r.font.bold = True
        r.font.color.rgb = rgb(bullet_color)
        r = p.add_run()
        r.text = item
        r.font.name = "Aptos"
        r.font.size = Pt(size)
        r.font.color.rgb = rgb(color)
    return box


def connector(slide, x1, y1, x2, y2, color="line", width=2, arrow=True):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = rgb(color)
    c.line.width = Pt(width)
    if arrow:
        c.line.end_arrowhead = True
    return c


def pill(slide, label, x, y, w, fill="mint", color="green", size=10):
    shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, 0.32, fill, radius=True)
    text(slide, label, x + 0.08, y + 0.045, w - 0.16, 0.22, size=size, color=color,
         bold=True, align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE)


def card(slide, x, y, w, h, title, body=None, accent="teal", fill="white",
         title_size=17, body_size=13):
    shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill, line="line")
    shape(slide, MSO_SHAPE.RECTANGLE, x, y, 0.07, h, accent, radius=False)
    text(slide, title, x + 0.23, y + 0.19, w - 0.44, 0.42, size=title_size,
         color="ink", bold=True)
    if body:
        text(slide, body, x + 0.23, y + 0.74, w - 0.44, h - 0.88,
             size=body_size, color="muted")


def base_slide(prs, title, section, subtitle=None, dark=False):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg = s.background.fill
    bg.solid()
    bg.fore_color.rgb = rgb("navy" if dark else "paper")
    if dark:
        text(s, section.upper(), 0.62, 0.34, 4.8, 0.25, 10, "teal", True)
        text(s, title, 0.62, 0.78, 12.1, 0.6, 27, "white", True)
        if subtitle:
            text(s, subtitle, 0.65, 1.43, 11.9, 0.43, 13, "slate")
    else:
        text(s, section.upper(), 0.62, 0.28, 4.8, 0.22, 9, "blue", True)
        text(s, title, 0.62, 0.66, 12.1, 0.58, 26, "navy", True)
        if subtitle:
            text(s, subtitle, 0.65, 1.29, 11.9, 0.36, 12, "muted")
    return s


def footer(slide, n, dark=False):
    color = "71809A" if dark else "94A3B8"
    text(slide, "GUARDUTY  /  EKS AI OPS", 0.62, 7.16, 4.5, 0.18,
         8, color, True)
    text(slide, f"{n:02d}", 12.22, 7.12, 0.46, 0.22, 9, color, True,
         align=PP_ALIGN.RIGHT)


def new_slide(prs, title, section, subtitle=None, dark=False):
    s = base_slide(prs, title, section, subtitle, dark)
    footer(s, len(prs.slides), dark)
    return s


def make_deck():
    prs = Presentation()
    prs.slide_width = Inches(SW)
    prs.slide_height = Inches(SH)
    prs.core_properties.title = "Guarduty AI Ops — EKS threat detection and response"
    prs.core_properties.subject = "GuardDuty, evidence analysis, policy gates, and automated EKS containment"
    prs.core_properties.author = "Guarduty project team"
    prs.core_properties.keywords = "AWS, EKS, GuardDuty, AI Ops, incident response"

    # 1 — Cover
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = rgb("navy")
    shape(s, MSO_SHAPE.RECTANGLE, 9.7, 0, 3.64, 7.5, "navy2", radius=False)
    for i in range(6):
        shape(s, MSO_SHAPE.OVAL, 10.05 + (i % 2) * 1.25, 0.55 + i * 0.92,
              0.13, 0.13, "teal" if i % 2 == 0 else "blue", radius=False)
    text(s, "PROJECT PRESENTATION  /  NOV 2026", 0.78, 0.7, 6.8, 0.3,
         11, "teal", True)
    text(s, "Guarduty\nAI Ops", 0.78, 1.47, 7.2, 1.85, 39, "white", True)
    text(s, "Phát hiện sự cố, phân tích bằng chứng\nvà tự ứng phó có kiểm soát trên Amazon EKS",
         0.82, 3.65, 7.45, 0.95, 19, "slate")
    pill(s, "DETECT", 0.84, 5.35, 1.05, fill="navy2", color="teal", size=10)
    text(s, "→", 2.0, 5.36, 0.3, 0.25, 17, "white", True)
    pill(s, "ANALYZE", 2.32, 5.35, 1.25, fill="navy2", color="white", size=10)
    text(s, "→", 3.72, 5.36, 0.3, 0.25, 17, "white", True)
    pill(s, "DECIDE", 4.04, 5.35, 1.1, fill="navy2", color="orange", size=10)
    text(s, "→", 5.28, 5.36, 0.3, 0.25, 17, "white", True)
    pill(s, "RESPOND", 5.61, 5.35, 1.34, fill="navy2", color="white", size=10)
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 10.25, 2.08, 2.35, 2.65, "white")
    text(s, "AWS SANDBOX", 10.55, 2.38, 1.8, 0.28, 10, "blue", True,
         align=PP_ALIGN.CENTER)
    for i, (label, col) in enumerate([("GuardDuty", "orange"), ("EventBridge", "blue"),
                                      ("Step Functions", "teal"), ("EKS response", "green")]):
        y = 2.92 + i * 0.43
        shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 10.58, y, 1.7, 0.3, "slate")
        text(s, label, 10.67, y + 0.035, 1.52, 0.21, 10, col, True,
             align=PP_ALIGN.CENTER)
    text(s, "Evidence-first analysis  ·  Deterministic policy  ·  Reversible action",
         0.82, 6.62, 8.7, 0.3, 11, "slate")
    footer(s, 1, True)

    # 2 — Problem
    s = new_slide(prs, "Phát hiện thôi chưa giải quyết được incident", "01 / Problem",
                  "Khoảng trống nằm giữa finding và corrective action.")
    cols = [
        (0.68, "01", "Detect", "Có alert, nhưng đội vận hành cần biết resource nào đang bị ảnh hưởng và mức khẩn cấp ra sao.", "blue"),
        (4.57, "02", "Analyze", "Dữ liệu nằm ở nhiều nơi: finding, process, pod, audit log và lịch sử thay đổi.", "teal"),
        (8.46, "03", "Respond", "Thao tác tay chậm; tự động sửa quá rộng lại có thể làm gián đoạn ứng dụng.", "orange"),
    ]
    for x, num, title, body, accent in cols:
        card(s, x, 2.0, 3.55, 2.55, title, body, accent, title_size=19, body_size=15)
        pill(s, num, x + 0.24, 4.86, 0.62, fill="slate", color=accent, size=10)
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 0.68, 5.55, 11.32, 0.86, "navy")
    text(s, "Mục tiêu", 0.96, 5.79, 1.2, 0.28, 14, "teal", True)
    text(s, "Tự động hoá phần có evidence + policy rõ; chuyển phần còn mơ hồ sang notify-only.",
         2.16, 5.76, 9.4, 0.34, 15, "white", True)

    # 3 — Flow
    s = new_slide(prs, "Một luồng từ finding đến hành động có kiểm chứng", "02 / Workflow",
                  "Mỗi bước có đầu vào, quyết định và bằng chứng để truy vết.", dark=True)
    items = [
        (0.58, "1", "DETECT", "GuardDuty\nEKS + runtime", "blue"),
        (3.13, "2", "INGEST", "EventBridge\n→ Step Functions", "teal"),
        (5.68, "3", "ANALYZE", "Evidence +\nhypothesis", "orange"),
        (8.23, "4", "DECIDE", "Deterministic\npolicy gates", "blue"),
        (10.78, "5", "RESPOND", "Notify or\ncontain / release", "teal"),
    ]
    for i, (x, num, title, body, accent) in enumerate(items):
        shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, x, 2.44, 1.92, 1.55, "navy2", line="3A4A66")
        shape(s, MSO_SHAPE.OVAL, x + 0.16, 2.61, 0.36, 0.36, accent, radius=False)
        text(s, num, x + 0.16, 2.66, 0.36, 0.19, 10, "white", True, align=PP_ALIGN.CENTER)
        text(s, title, x + 0.61, 2.64, 1.2, 0.25, 11, accent, True)
        text(s, body, x + 0.18, 3.15, 1.57, 0.57, 13, "white", True)
        if i < len(items) - 1:
            connector(s, x + 1.98, 3.2, x + 2.45, 3.2, "teal", 2)
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 2.82, 4.65, 3.26, 0.82, "navy2", line="3A4A66")
    text(s, "Evidence không đủ / scope lệch", 3.08, 4.9, 2.78, 0.24, 12, "white", True,
         align=PP_ALIGN.CENTER)
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 7.25, 4.65, 3.25, 0.82, "navy2", line="3A4A66")
    text(s, "Target rõ + playbook cho phép", 7.48, 4.9, 2.8, 0.24, 12, "white", True,
         align=PP_ALIGN.CENTER)
    connector(s, 8.9, 4.04, 4.46, 4.58, "orange", 1, arrow=True)
    connector(s, 9.75, 4.04, 8.85, 4.58, "teal", 1, arrow=True)
    text(s, "NOTIFY-ONLY", 3.54, 5.77, 1.9, 0.28, 11, "orange", True,
         align=PP_ALIGN.CENTER)
    text(s, "QUARANTINE → VERIFY → RELEASE", 7.3, 5.77, 3.2, 0.28, 11, "teal", True,
         align=PP_ALIGN.CENTER)

    # 4 — Architecture
    s = new_slide(prs, "Kiến trúc AWS của phòng lab", "03 / Architecture",
                  "Các dịch vụ được nối theo luồng ứng cứu; policy giữ quyền cho phép hành động.")
    xrow = [0.6, 3.12, 5.64, 8.16, 10.68]
    arch = [
        ("SOURCES", "GuardDuty\nEKS Protection\nRuntime Monitoring", "blue"),
        ("ROUTING", "EventBridge\nAttack sequence\nEKS runtime", "teal"),
        ("ORCHESTRATE", "Step Functions\nRetry · dedup\nDLQ", "orange"),
        ("ANALYZE", "Lambda analyzer\nEvidence +\nhypothesis", "blue"),
        ("DECIDE", "Policy gates\nExact scope\nAllowlist", "teal"),
    ]
    for x, (tag, body, color) in zip(xrow, arch):
        shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, x, 2.07, 2.05, 1.68, "white", line="line")
        pill(s, tag, x + 0.16, 2.26, 1.16, fill="slate", color=color, size=8)
        text(s, body, x + 0.17, 2.78, 1.72, 0.76, 13, "ink", True)
    for x in xrow[:-1]:
        connector(s, x + 2.08, 2.9, x + 2.47, 2.9, "blue", 1.8)
    # Evidence plane
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 5.4, 4.42, 3.12, 1.24, "mint")
    text(s, "EVIDENCE PLANE", 5.7, 4.64, 2.5, 0.24, 10, "green", True,
         align=PP_ALIGN.CENTER)
    text(s, "S3: finding/evidence  ·  DynamoDB: incident state", 5.63, 5.03, 2.67, 0.43,
         12, "ink", True, align=PP_ALIGN.CENTER)
    connector(s, 6.7, 3.78, 6.7, 4.35, "teal", 1.5)
    # Action and notification
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 8.67, 4.42, 1.82, 1.24, "amber")
    text(s, "NOTIFY", 8.88, 4.66, 1.4, 0.22, 10, "orange", True, align=PP_ALIGN.CENTER)
    text(s, "SNS\nsubscriber pending", 8.88, 5.0, 1.4, 0.46, 12, "ink", True, align=PP_ALIGN.CENTER)
    connector(s, 9.13, 3.78, 9.45, 4.34, "orange", 1.5)
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 10.75, 4.42, 1.92, 1.24, "mint")
    text(s, "CONTAIN", 10.97, 4.66, 1.46, 0.22, 10, "green", True, align=PP_ALIGN.CENTER)
    text(s, "Remediator\nNetworkPolicy / EKS", 10.91, 5.0, 1.62, 0.46, 11, "ink", True, align=PP_ALIGN.CENTER)
    connector(s, 9.95, 3.1, 11.65, 4.33, "teal", 1.5)
    text(s, "Quarantine có TTL 15 phút · giữ pod để điều tra · gỡ policy đúng action ID",
         0.9, 6.25, 11.5, 0.32, 12, "muted", True, align=PP_ALIGN.CENTER)

    # 5 — Detection
    s = new_slide(prs, "Detect: hai nguồn tín hiệu cho EKS", "04 / Detect",
                  "Audit activity cho biết thao tác Kubernetes; runtime telemetry cho biết hành vi trong workload.")
    card(s, 0.72, 2.02, 5.55, 2.85, "EKS Protection",
         "• Phân tích Kubernetes audit logs\n• Không cần cài agent trong pod\n• Bắt hoạt động control-plane và API",
         "blue", title_size=20, body_size=15)
    card(s, 7.02, 2.02, 5.55, 2.85, "Runtime Monitoring",
         "• GuardDuty-managed EKS agent trên node\n• Theo dõi process, file và network behavior\n• Coverage phải healthy để telemetry có ích",
         "teal", title_size=20, body_size=15)
    pill(s, "OBSERVED: 1 EKS CLUSTER · 2 WORKER NODES", 3.9, 5.42, 5.4,
         fill="navy", color="white", size=10)
    text(s, "Lưu ý: finding là tín hiệu cần điều tra; chưa tự chứng minh nguyên nhân gốc.",
         2.4, 6.15, 8.5, 0.3, 13, "muted", align=PP_ALIGN.CENTER)

    # 6 — Canary
    s = new_slide(prs, "Detection đã kiểm chứng bằng DNS canary", "05 / Live finding",
                  "Một truy vấn DNS được chủ động tạo từ pod demo theo hướng dẫn kiểm thử của AWS.", dark=True)
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 0.72, 2.02, 4.18, 3.8, "navy2", line="3A4A66")
    pill(s, "GUARDDUTY RUNTIME FINDING", 1.02, 2.32, 2.75, fill="navy", color="teal", size=9)
    text(s, "Backdoor:Runtime/\nC&CActivity.B!DNS", 1.02, 2.95, 3.56, 0.96, 21, "white", True)
    text(s, "Finding type", 1.05, 4.2, 1.3, 0.24, 10, "slate")
    text(s, "Severity 8 · High", 1.05, 4.57, 2.8, 0.34, 16, "orange", True)
    text(s, "DNS request bị GuardDuty ghi nhận; không thực hiện kết nối tới domain.",
         1.05, 5.08, 3.35, 0.49, 12, "slate")
    facts = [
        ("DOMAIN", "guarddutyc2activityb.com", "teal"),
        ("PROCESS", "nslookup / BusyBox", "blue"),
        ("WORKLOAD", "pod → container → EKS cluster", "orange"),
    ]
    for i, (label, value, color) in enumerate(facts):
        y = 2.22 + i * 1.15
        text(s, label, 5.65, y, 1.45, 0.23, 10, color, True)
        text(s, value, 7.15, y - 0.03, 4.8, 0.34, 17, "white", True)
        connector(s, 5.65, y + 0.53, 12.05, y + 0.53, "3A4A66", 0.8, arrow=False)
    text(s, "Canary có chủ đích — không phải dấu hiệu của xâm nhập thật.",
         5.65, 5.82, 6.0, 0.34, 13, "slate", italic=True)

    # 7 — Analysis
    s = new_slide(prs, "Analyze: biến finding thành evidence có cấu trúc", "06 / Analyze",
                  "Analyzer lấy lại finding chuẩn từ GuardDuty, trích resource context và ghi rõ phần chưa biết.")
    columns = [
        (0.74, "OBSERVED", ["Process: nslookup", "Domain: test canary", "Pod + container ID", "Cluster + node context"], "blue"),
        (4.88, "HYPOTHESIS", ["Runtime finding báo hành vi DNS đáng ngờ", "Process và workload nối được với nhau", "Confidence được gán theo evidence hiện có"], "teal"),
        (9.02, "GAPS", ["Không có user IAM actor trong finding", "Detective graph chưa truy vấn được", "Chưa kết luận root cause pháp chứng"], "orange"),
    ]
    for x, title, lines, color in columns:
        shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, x, 2.1, 3.55, 3.3, "white", line="line")
        pill(s, title, x + 0.25, 2.35, 1.38, fill="slate", color=color, size=9)
        bullets(s, lines, x + 0.26, 2.95, 3.05, 2.05, 13, "ink", 10, color)
    text(s, "Kết quả hiện tại: root-cause hypothesis, confidence medium — không phải AI answer.",
         1.1, 5.94, 11.1, 0.38, 14, "navy", True, align=PP_ALIGN.CENTER)

    # 8 — Policy
    s = new_slide(prs, "Decide: policy là ranh giới quyền hành động", "07 / Decide",
                  "AI hoặc finding có thể đề xuất; deterministic gates mới cho phép mutation.", dark=True)
    gates = [
        (0.8, "Finding type", "EKS attack sequence", "blue"),
        (3.15, "Severity", "Critical (≥ 9)", "orange"),
        (5.5, "Account / region", "Match sandbox", "teal"),
        (7.85, "Cluster / workload", "Exact target", "blue"),
        (10.2, "Pod opt-in", "Owner + safe scope", "teal"),
    ]
    for x, title, sub, color in gates:
        shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, x, 2.18, 1.92, 1.55, "navy2", line="3A4A66")
        text(s, title, x + 0.12, 2.48, 1.68, 0.29, 12, color, True, align=PP_ALIGN.CENTER)
        text(s, sub, x + 0.13, 3.0, 1.66, 0.42, 11, "white", align=PP_ALIGN.CENTER)
    for x in [2.77, 5.12, 7.47, 9.82]:
        text(s, "AND", x, 2.82, 0.36, 0.2, 9, "slate", True, align=PP_ALIGN.CENTER)
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 1.05, 4.55, 4.85, 1.1, "navy2", line="3A4A66")
    text(s, "Một điều kiện không đạt", 1.38, 4.78, 4.2, 0.28, 16, "orange", True,
         align=PP_ALIGN.CENTER)
    text(s, "NOTIFY-ONLY → SNS", 1.4, 5.13, 4.15, 0.25, 12, "white", True,
         align=PP_ALIGN.CENTER)
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 7.42, 4.55, 4.85, 1.1, "navy2", line="3A4A66")
    text(s, "Mọi điều kiện đạt", 7.76, 4.78, 4.2, 0.28, 16, "teal", True,
         align=PP_ALIGN.CENTER)
    text(s, "QUARANTINE exact pod → verify → release", 7.65, 5.13, 4.4, 0.25,
         11, "white", True, align=PP_ALIGN.CENTER)
    connector(s, 6.66, 3.83, 3.47, 4.49, "orange", 1.5)
    connector(s, 6.66, 3.83, 9.84, 4.49, "teal", 1.5)

    # 9 — Containment
    s = new_slide(prs, "Contain: cô lập hẹp, có hạn dùng và đường lui", "08 / Corrective action",
                  "Dùng Kubernetes NetworkPolicy cho pod đã opt-in; giữ nguyên pod và node để điều tra.")
    stages = [
        (0.88, "1", "Select", "Exact pod name\n+ opt-in label", "blue"),
        (4.16, "2", "Isolate", "Apply action-specific\nNetworkPolicy", "orange"),
        (7.44, "3", "Verify", "Check object and\ndata-plane behavior", "teal"),
        (10.72, "4", "Release", "After 15 minutes,\nremove exact policy", "green"),
    ]
    for x, n, title, body, color in stages:
        shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, x, 2.28, 1.78, 2.0, "white", line="line")
        shape(s, MSO_SHAPE.OVAL, x + 0.18, 2.47, 0.4, 0.4, color, radius=False)
        text(s, n, x + 0.18, 2.56, 0.4, 0.18, 10, "white", True, align=PP_ALIGN.CENTER)
        text(s, title, x + 0.2, 3.03, 1.37, 0.32, 16, "ink", True)
        text(s, body, x + 0.2, 3.55, 1.4, 0.5, 11, "muted")
        if x != 10.72:
            connector(s, x + 1.84, 3.25, x + 3.12, 3.25, "blue", 1.5)
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 1.1, 5.12, 11.08, 0.9, "navy")
    text(s, "Không xoá pod hàng loạt  ·  Không cách ly cluster  ·  Không để policy treo vô thời hạn",
         1.42, 5.41, 10.45, 0.28, 14, "white", True, align=PP_ALIGN.CENTER)

    # 10 — Reliability
    s = new_slide(prs, "Reliability: giữ được dấu vết và xử lý lỗi", "09 / Operations",
                  "Tự động hoá có ích khi biết event nào vào, trạng thái nào đổi và lỗi được giữ ở đâu.", dark=True)
    left = [
        ("Retry bounded", "Không lặp vô hạn khi dịch vụ downstream lỗi."),
        ("DynamoDB dedup", "Một finding ID không tạo action trùng."),
        ("SQS DLQ", "Event không khởi chạy được workflow được giữ lại."),
    ]
    right = [
        ("S3 evidence", "Finding canonical và analysis để điều tra lại."),
        ("CloudWatch alarms", "Theo dõi workflow failure và DLQ."),
        ("SNS publish", "Notify-only đã publish; subscriber còn thiếu."),
    ]
    for i, (title, body) in enumerate(left):
        y = 2.0 + i * 1.18
        pill(s, f"0{i+1}", 0.9, y + 0.07, 0.6, fill="navy2", color="teal", size=9)
        text(s, title, 1.75, y, 3.0, 0.28, 16, "white", True)
        text(s, body, 1.75, y + 0.39, 4.0, 0.35, 12, "slate")
    for i, (title, body) in enumerate(right):
        y = 2.0 + i * 1.18
        pill(s, f"0{i+4}", 7.0, y + 0.07, 0.6, fill="navy2", color="orange", size=9)
        text(s, title, 7.85, y, 3.0, 0.28, 16, "white", True)
        text(s, body, 7.85, y + 0.39, 4.45, 0.35, 12, "slate")
    connector(s, 6.55, 2.08, 6.55, 5.74, "3A4A66", 1, arrow=False)
    text(s, "Evidence retention: S3 90 ngày  ·  DynamoDB PITR + TTL 90 ngày",
         1.2, 6.0, 10.9, 0.3, 12, "teal", True, align=PP_ALIGN.CENTER)

    # 11 — Demo
    s = new_slide(prs, "Demo: từ coverage đến finding và response decision", "10 / Live demo",
                  "Thứ tự demo để người nghe thấy cả tín hiệu, phân tích và cleanup.")
    demo = [
        ("01", "Kiểm tra sandbox", "AWS caller identity · EKS status · GuardDuty coverage"),
        ("02", "Chạy hoạt động giới hạn", "HTTP 200 · TCP scan một service · scoped API query"),
        ("03", "Tạo DNS canary", "Một lookup tới domain test của AWS từ pod demo"),
        ("04", "Xem finding + workflow", "EventBridge → Step Functions · policy decision · S3/DynamoDB/SNS"),
        ("05", "Xác nhận cleanup", "Pod healthy · không còn NetworkPolicy canary · alarms/DLQ OK"),
    ]
    for i, (num, title, desc) in enumerate(demo):
        y = 1.88 + i * 0.88
        shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 0.86, y, 0.62, 0.54, "navy")
        text(s, num, 0.86, y + 0.16, 0.62, 0.2, 11, "teal", True, align=PP_ALIGN.CENTER)
        text(s, title, 1.82, y + 0.02, 3.0, 0.28, 15, "ink", True)
        text(s, desc, 4.95, y + 0.03, 7.2, 0.32, 13, "muted")
    pill(s, "LƯU Ý: DNS CANARY ĐƯỢC CHỦ ĐỘNG TẠO — KHÔNG KẾT NỐI TỚI DOMAIN", 2.55, 6.43,
         8.2, fill="amber", color="orange", size=9)

    # 12 — Results
    s = new_slide(prs, "Kết quả: điều gì đã được chứng minh?", "11 / Results",
                  "Tách rõ finding thật, synthetic fixture và phần chưa kiểm chứng.")
    rows = [
        ("GuardDuty runtime DNS finding", "Thật — severity 8; process, pod, container, cluster", "teal"),
        ("EventBridge → Step Functions", "Tự động route finding mới; workflow SUCCEEDED", "teal"),
        ("Evidence + notification", "S3/DynamoDB lưu; SNS publish OK, subscriber chưa có", "teal"),
        ("AttackSequence finding", "Chưa tạo finding thật; workshop 5.3.2 chưa chạy", "orange"),
        ("Auto-quarantine từ attack sequence", "Chưa kiểm chứng end-to-end với finding thật", "orange"),
    ]
    for i, (what, state, color) in enumerate(rows):
        y = 2.0 + i * 0.78
        shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 0.78, y, 11.78, 0.58, "white", line="line")
        shape(s, MSO_SHAPE.OVAL, 1.02, y + 0.18, 0.2, 0.2, color, radius=False)
        text(s, what, 1.47, y + 0.15, 4.75, 0.26, 13, "ink", True)
        text(s, state, 6.15, y + 0.15, 6.0, 0.26, 12, "muted")

    # 13 — Gaps
    s = new_slide(prs, "Giới hạn hiện tại và bước tiếp theo", "12 / Roadmap",
                  "Bản demo ưu tiên an toàn, truy vết và policy rõ trước khi mở rộng tự động hoá.", dark=True)
    gaps = [
        ("01", "Attack sequence + containment", "Chạy workshop riêng; chứng minh correlation và quarantine thật.", "orange"),
        ("02", "Người nhận cảnh báo", "Subscribe SNS và chạy game-day kiểm tra notify/alert.", "blue"),
        ("03", "Coverage và vận hành", "Thêm coverage-health alarm, dashboard và SLO.", "teal"),
        ("04", "Root cause + AI", "Bật Detective/Bedrock khi account policy cho phép; citation và confidence.", "orange"),
    ]
    for i, (num, title, body, color) in enumerate(gaps):
        x = 0.83 + (i % 2) * 6.08
        y = 2.0 + (i // 2) * 1.75
        shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, 5.6, 1.36, "navy2", line="3A4A66")
        pill(s, num, x + 0.22, y + 0.2, 0.58, fill="navy", color=color, size=9)
        text(s, title, x + 1.0, y + 0.2, 4.3, 0.3, 15, "white", True)
        text(s, body, x + 1.0, y + 0.66, 4.27, 0.48, 12, "slate")
    text(s, "Không áp dụng manifest workshop rủi ro cao nguyên trạng.",
         1.12, 6.08, 11.0, 0.32, 13, "orange", True, align=PP_ALIGN.CENTER)

    # 14 — Close
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = rgb("navy")
    pill(s, "KEY TAKEAWAY", 0.9, 0.8, 1.65, fill="navy2", color="teal", size=9)
    text(s, "AI Ops cần tự động hoá\nđúng phạm vi — không chỉ nhanh.",
         0.9, 1.65, 8.9, 1.7, 32, "white", True)
    text(s, "Evidence giải thích. Policy cho phép.\nAction có giới hạn và đường rollback.",
         0.94, 3.75, 7.9, 0.8, 18, "slate")
    for i, (label, color) in enumerate([("EVIDENCE", "blue"), ("POLICY", "orange"),
                                        ("REVERSIBLE ACTION", "teal")]):
        x = 0.95 + i * 2.55
        pill(s, label, x, 5.45, 2.1, fill="navy2", color=color, size=9)
    text(s, "GUARDUTY  /  EKS AI OPS", 0.95, 6.74, 4.2, 0.2, 9, "slate", True)
    footer(s, 14, True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT)
    print(f"Wrote {OUT} ({len(prs.slides)} slides)")


if __name__ == "__main__":
    make_deck()
