"""Generate all figures/diagrams/charts for the DermAI FYP report.
Outputs PNGs into Docs/report_assets/.
Run with the fyp env python.
"""
from __future__ import annotations
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Ellipse, Rectangle
from matplotlib.lines import Line2D

OUT = os.path.join(os.path.dirname(__file__), "report_assets")
os.makedirs(OUT, exist_ok=True)

# DermAI palette
BLUE   = "#2563EB"
DBLUE  = "#1E3A8A"
LBLUE  = "#DBEAFE"
GREEN  = "#16A34A"
LGREEN = "#DCFCE7"
AMBER  = "#D97706"
LAMBER = "#FEF3C7"
RED    = "#DC2626"
GREY   = "#475569"
LGREY  = "#E2E8F0"
INK    = "#0F172A"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})

CLASSES = ["Acne", "Atopic Dermatitis", "Eczema", "Healthy",
           "Hyper Pigmentation", "Melanoma", "Psoriasis", "Seborrheic Keratoses"]

# Confusion matrix (rows = actual, cols = predicted) from the clean test set
CM = np.array([
    [269,  1,  3,   0,  0,   0,  1,  2],
    [  9,116, 14,   1,  2,   0, 17,  1],
    [  1, 11,121,   1,  1,   0, 16,  1],
    [  1,  0,  1, 178,  0,   0,  2,  0],
    [  0,  0,  0,   0, 87,   0,  0,  0],
    [  0,  0,  0,   0,  0, 178,  0,  2],
    [  3, 20,  7,   0,  1,   2,127,  5],
    [  4,  2,  5,   1,  0,   1,  4, 96],
])
TRAIN_COUNTS = [11482, 6660, 6336, 7623, 3618, 7560, 6885, 4725]
VAL_COUNTS   = [274, 158, 150, 181, 86, 180, 163, 112]
TEST_COUNTS  = [276, 160, 152, 182, 87, 180, 165, 113]


def save(fig, name):
    p = os.path.join(OUT, name)
    fig.savefig(p, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("saved", name)


# ----------------------------------------------------------------------------
# Helper: rounded box with centered (multiline) text
# ----------------------------------------------------------------------------
def box(ax, x, y, w, h, text, fc=LBLUE, ec=DBLUE, tc=INK, fs=10, bold=False, rad=0.02):
    p = FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                       boxstyle=f"round,pad=0.005,rounding_size={rad}",
                       fc=fc, ec=ec, lw=1.6, zorder=2)
    ax.add_patch(p)
    ax.text(x, y, text, ha="center", va="center", fontsize=fs,
            color=tc, zorder=3, fontweight=("bold" if bold else "normal"))
    return (x, y, w, h)


def arrow(ax, x1, y1, x2, y2, color=GREY, style="-|>", lw=1.8, ls="-", rad=0.0):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                        mutation_scale=16, color=color, lw=lw,
                        linestyle=ls, zorder=1,
                        connectionstyle=f"arc3,rad={rad}")
    ax.add_patch(a)


def diamond(ax, x, y, w, h, text, fc=LAMBER, ec=AMBER, fs=9):
    pts = [(x, y + h / 2), (x + w / 2, y), (x, y - h / 2), (x - w / 2, y)]
    poly = plt.Polygon(pts, closed=True, fc=fc, ec=ec, lw=1.6, zorder=2)
    ax.add_patch(poly)
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, zorder=3)


def clean(ax, xlim, ylim):
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.axis("off")
    ax.set_aspect("equal", adjustable="box")


# ============================================================================
# 1. WATERFALL METHODOLOGY
# ============================================================================
def fig_waterfall():
    fig, ax = plt.subplots(figsize=(9, 6.2))
    stages = ["Requirement\nAnalysis", "System\nDesign", "Implementation",
              "Integration &\nTesting", "Deployment", "Maintenance"]
    cols = [BLUE, "#2F6FE0", "#3B82F6", "#2563EB", DBLUE, "#1E40AF"]
    n = len(stages)
    w, h = 2.6, 0.95
    x0, y0 = 0.4, 6.0
    dx, dy = 1.55, -1.0
    centers = []
    for i, s in enumerate(stages):
        x = x0 + i * dx + w / 2
        y = y0 + i * dy
        box(ax, x, y, w, h, s, fc=LBLUE, ec=cols[i], tc=INK, fs=10.5, bold=True)
        centers.append((x, y))
    for i in range(n - 1):
        (x1, y1), (x2, y2) = centers[i], centers[i + 1]
        arrow(ax, x1 + w / 2 - 0.15, y1 - h / 2, x2 - w / 2 + 0.15, y2 + h / 2,
              color=DBLUE, lw=2.0)
    ax.text(0.4, 6.95, "Waterfall Development Model — DermAI",
            fontsize=13, fontweight="bold", color=DBLUE)
    clean(ax, (-0.2, 12.5), (0.2, 7.4))
    ax.set_aspect("auto")
    save(fig, "fig_waterfall.png")


# ============================================================================
# 2. SYSTEM ARCHITECTURE
# ============================================================================
def fig_architecture():
    fig, ax = plt.subplots(figsize=(10.5, 7.4))
    # layer bands
    bands = [
        (8.4, "PRESENTATION LAYER", LGREEN),
        (6.3, "APPLICATION / API LAYER (FastAPI)", LBLUE),
        (3.4, "AI / INFERENCE LAYER", LAMBER),
        (1.0, "DATA LAYER", LGREY),
    ]
    for yc, label, col in bands:
        ax.add_patch(Rectangle((0.1, yc - 0.9), 11.8, 1.9 if label.startswith("AI") else 1.6,
                     fc=col, ec="none", alpha=0.35, zorder=0))
        ax.text(0.25, yc + (0.92 if label.startswith("AI") else 0.62), label, fontsize=9.5,
                fontweight="bold", color=GREY, zorder=1)

    # presentation
    box(ax, 2.6, 8.5, 2.7, 0.9, "Mobile App\n(React Native / Expo)", fc="white", ec=GREEN, bold=True, fs=10)
    box(ax, 6.0, 8.5, 2.7, 0.9, "Web App\n(SPA, served at /app)", fc="white", ec=GREEN, bold=True, fs=10)
    box(ax, 9.4, 8.5, 2.7, 0.9, "Doctor / Admin\nConsole", fc="white", ec=GREEN, bold=True, fs=10)

    # API layer
    box(ax, 2.3, 6.3, 2.5, 0.85, "Auth &\nToken Service", fc="white", ec=BLUE, fs=9.5)
    box(ax, 5.0, 6.3, 2.4, 0.85, "Diagnose &\nChat Routes", fc="white", ec=BLUE, fs=9.5)
    box(ax, 7.6, 6.3, 2.4, 0.85, "History &\nReport Routes", fc="white", ec=BLUE, fs=9.5)
    box(ax, 10.1, 6.3, 2.4, 0.85, "Consult &\nVideo Routes", fc="white", ec=BLUE, fs=9.5)

    # AI layer
    box(ax, 1.9, 3.5, 2.3, 1.0, "Mobile SAM\nSegmentation\n(lesion region)", fc="white", ec=AMBER, fs=9)
    box(ax, 4.5, 3.5, 2.3, 1.0, "ConvNeXt-Tiny\nClassifier\n(8 classes)", fc="white", ec=AMBER, bold=True, fs=9)
    box(ax, 7.1, 3.5, 2.3, 1.0, "Decision Gate\n(confidence /\nentropy / OOD)", fc="white", ec=AMBER, fs=9)
    box(ax, 9.9, 3.5, 2.6, 1.0, "LLM Orchestrator\n(Gemini 2.5 /\nscripted bank)", fc="white", ec=AMBER, fs=9)

    # data layer
    box(ax, 2.6, 1.0, 2.6, 0.85, "SQLite DB\n(users, tokens, history)", fc="white", ec=GREY, fs=9)
    box(ax, 6.0, 1.0, 2.6, 0.85, "File Store\n(uploads, reports)", fc="white", ec=GREY, fs=9)
    box(ax, 9.4, 1.0, 2.6, 0.85, "Model Weights\n(.pth, classes.json)", fc="white", ec=GREY, fs=9)

    # vertical connectors
    arrow(ax, 6.0, 8.02, 6.0, 7.2, color=DBLUE, lw=2)
    arrow(ax, 6.0, 5.85, 6.0, 5.0, color=AMBER, lw=2)
    arrow(ax, 6.0, 2.95, 6.0, 1.9, color=GREY, lw=2)
    # pipeline arrows inside AI layer
    arrow(ax, 3.05, 3.5, 3.35, 3.5, color=AMBER)
    arrow(ax, 5.65, 3.5, 5.95, 3.5, color=AMBER)
    arrow(ax, 8.25, 3.5, 8.6, 3.5, color=AMBER)

    ax.text(6.0, 9.7, "DermAI — System Architecture", fontsize=14, fontweight="bold",
            color=DBLUE, ha="center")
    clean(ax, (0, 12), (0, 10.1))
    ax.set_aspect("auto")
    save(fig, "fig_architecture.png")


# ============================================================================
# 3. FLOWCHART
# ============================================================================
def fig_flowchart():
    fig, ax = plt.subplots(figsize=(8.2, 12))
    cx = 5.2          # main spine
    sx = 1.7          # side-branch column (left)
    def term(y, t, fc=LGREEN, ec=GREEN):
        p = FancyBboxPatch((cx - 1.6, y - 0.4), 3.2, 0.8,
                           boxstyle="round,pad=0.02,rounding_size=0.4",
                           fc=fc, ec=ec, lw=1.6, zorder=2)
        ax.add_patch(p)
        ax.text(cx, y, t, ha="center", va="center", fontsize=10.5, fontweight="bold", zorder=3)
    def proc(y, t, fc=LBLUE, ec=BLUE, w=4.0):
        box(ax, cx, y, w, 0.82, t, fc=fc, ec=ec, fs=9.5)
    def sidebox(y, t, fc=LAMBER, ec=AMBER):
        box(ax, sx, y, 2.4, 0.82, t, fc=fc, ec=ec, fs=8.5)

    # Start
    term(14.0, "Start")
    arrow(ax, cx, 13.6, cx, 13.25, color=GREY)
    # Logged in?
    diamond(ax, cx, 12.6, 3.0, 1.05, "Logged in?")
    ax.text(cx - 1.7, 12.85, "No", fontsize=9, color=RED, ha="right")
    arrow(ax, cx - 1.5, 12.6, sx + 1.2, 12.6, color=GREY)         # to side
    sidebox(12.6, "Login /\nSign-up")
    arrow(ax, sx, 12.19, sx, 11.55, color=GREY)                  # side down
    arrow(ax, sx, 11.55, cx - 2.0, 11.55, color=GREY)            # rejoin spine
    ax.text(cx + 0.2, 11.95, "Yes", fontsize=9, color=GREEN)
    arrow(ax, cx, 12.07, cx, 11.25, color=GREY)                  # yes straight down
    # Medical history?
    diamond(ax, cx, 10.6, 3.2, 1.05, "Medical history\ncompleted?", fc=LAMBER, ec=AMBER, fs=8.5)
    ax.text(cx - 1.8, 10.85, "No", fontsize=9, color=RED, ha="right")
    arrow(ax, cx - 1.6, 10.6, sx + 1.2, 10.6, color=GREY)
    sidebox(10.6, "Fill medical\nhistory form")
    arrow(ax, sx, 10.19, sx, 9.55, color=GREY)
    arrow(ax, sx, 9.55, cx - 2.0, 9.55, color=GREY)
    ax.text(cx + 0.2, 9.95, "Yes", fontsize=9, color=GREEN)
    arrow(ax, cx, 10.07, cx, 9.25, color=GREY)
    # capture
    proc(8.7, "Capture / upload skin image\n+ select body region")
    arrow(ax, cx, 8.29, cx, 7.95, color=GREY)
    proc(7.5, "Mobile SAM segments lesion region")
    arrow(ax, cx, 7.09, cx, 6.75, color=GREY)
    proc(6.3, "ConvNeXt classifies disease + confidence")
    arrow(ax, cx, 5.89, cx, 5.45, color=GREY)
    # gate
    diamond(ax, cx, 4.75, 3.4, 1.1, "Confident &\nin-distribution?", fc=LAMBER, ec=AMBER, fs=8.5)
    ax.text(cx - 1.85, 5.0, "No", fontsize=9, color=RED, ha="right")
    arrow(ax, cx - 1.7, 4.75, sx + 1.2, 4.75, color=GREY)
    sidebox(4.75, "Flag low-conf. /\nout-of-scope\n-> retake", fc="#FEE2E2", ec=RED)
    arrow(ax, sx, 4.34, sx, 3.7, color=GREY)
    arrow(ax, sx, 3.7, cx - 2.1, 3.7, color=GREY)
    ax.text(cx + 0.2, 4.1, "Yes", fontsize=9, color=GREEN)
    arrow(ax, cx, 4.2, cx, 3.4, color=GREY)
    # LLM
    proc(2.55, "LLM asks disease-specific questions\n+ fuse symptoms into result")
    arrow(ax, cx, 2.14, cx, 1.8, color=GREY)
    proc(0.95, "Show diagnosis -> PDF report /\nconsult doctor", fc=LGREEN, ec=GREEN)
    arrow(ax, cx, 0.54, cx, 0.2, color=GREY)
    term(-0.4, "End", fc=LGREEN, ec=GREEN)
    ax.text(cx, 14.8, "DermAI — Application Flowchart", fontsize=13, fontweight="bold",
            color=DBLUE, ha="center")
    clean(ax, (0.2, 9.5), (-0.9, 15.2))
    ax.set_aspect("auto")
    save(fig, "fig_flowchart.png")


# ============================================================================
# 4. SEQUENCE DIAGRAM
# ============================================================================
def fig_sequence():
    fig, ax = plt.subplots(figsize=(11, 7.2))
    actors = ["Patient", "Mobile/Web\nUI", "FastAPI\nBackend", "AI Pipeline\n(SAM+ConvNeXt)",
              "LLM\nOrchestrator", "Database"]
    xs = [1.2, 3.2, 5.4, 7.6, 9.6, 11.4]
    top, bot = 6.6, 0.4
    for x, a in zip(xs, actors):
        box(ax, x, top + 0.35, 1.7, 0.7, a, fc=LBLUE, ec=DBLUE, fs=8.5, bold=True)
        ax.add_line(Line2D([x, x], [top, bot], color=GREY, ls=(0, (4, 3)), lw=1))
    def msg(y, i, j, t, ret=False):
        x1, x2 = xs[i], xs[j]
        ls = (0, (5, 3)) if ret else "-"
        arrow(ax, x1, y, x2, y, color=(GREY if ret else DBLUE), lw=1.5, ls=ls)
        mid = (x1 + x2) / 2
        ax.text(mid, y + 0.12, t, ha="center", fontsize=8, color=INK)
    msg(6.2, 0, 1, "Capture image + body region")
    msg(5.8, 1, 2, "POST /diagnose")
    msg(5.4, 2, 3, "segment + classify")
    msg(5.0, 3, 2, "disease, confidence, insights", ret=True)
    msg(4.6, 2, 4, "request follow-up questions")
    msg(4.2, 4, 1, "disease-specific question", ret=True)
    msg(3.8, 0, 1, "answer symptom question")
    msg(3.4, 1, 4, "submit answers")
    msg(3.0, 4, 2, "fused preliminary result", ret=True)
    msg(2.6, 2, 5, "store screening + history")
    msg(2.2, 5, 2, "ack", ret=True)
    msg(1.8, 2, 1, "result + PDF report", ret=True)
    msg(1.4, 1, 0, "show diagnosis / consult option", ret=True)
    ax.text(6.2, 7.6, "DermAI — Sequence Diagram (Screening Flow)", fontsize=13,
            fontweight="bold", color=DBLUE, ha="center")
    clean(ax, (0.2, 12.4), (0.2, 8.0))
    ax.set_aspect("auto")
    save(fig, "fig_sequence.png")


# ============================================================================
# 5. USE CASE DIAGRAM
# ============================================================================
def fig_usecase():
    fig, ax = plt.subplots(figsize=(11, 7.6))
    # system boundary
    ax.add_patch(Rectangle((3.2, 0.4), 5.6, 8.4, fc="none", ec=DBLUE, lw=1.8))
    ax.text(6.0, 8.5, "DermAI System", fontsize=11, fontweight="bold", color=DBLUE, ha="center")

    def actor(x, y, name):
        ax.add_patch(Circle((x, y + 0.45), 0.18, fc="white", ec=INK, lw=1.6))
        ax.add_line(Line2D([x, x], [y + 0.27, y - 0.25], color=INK, lw=1.6))
        ax.add_line(Line2D([x - 0.28, x + 0.28], [y + 0.1, y + 0.1], color=INK, lw=1.6))
        ax.add_line(Line2D([x, x - 0.22], [y - 0.25, y - 0.6], color=INK, lw=1.6))
        ax.add_line(Line2D([x, x + 0.22], [y - 0.25, y - 0.6], color=INK, lw=1.6))
        ax.text(x, y - 0.9, name, ha="center", fontsize=10, fontweight="bold")

    actor(1.2, 5.6, "Patient")
    actor(1.2, 2.3, "Doctor")
    actor(10.8, 5.0, "Admin")

    ucs = [
        (4.4, 8.0, "Register / Login"),
        (7.6, 8.0, "Manage medical history"),
        (4.4, 6.9, "Upload / capture image"),
        (7.6, 6.9, "Get AI diagnosis"),
        (4.4, 5.8, "Answer follow-up Qs"),
        (7.6, 5.8, "View screenings"),
        (4.4, 4.7, "Download PDF report"),
        (7.6, 4.7, "Request consultation"),
        (4.4, 3.6, "Review patient case"),
        (7.6, 3.6, "Video consultation"),
        (6.0, 2.5, "Add solution notes"),
        (6.0, 1.4, "Verify doctors / admins"),
    ]
    pos = {}
    for x, y, t in ucs:
        ax.add_patch(Ellipse((x, y), 2.5, 0.85, fc=LBLUE, ec=BLUE, lw=1.4, zorder=2))
        ax.text(x, y, t, ha="center", va="center", fontsize=8.3, zorder=3)
        pos[t] = (x, y)

    def link(actor_xy, t):
        x, y = pos[t]
        ax.add_line(Line2D([actor_xy[0], x - 1.25 if x < 6 else x + 1.25],
                           [actor_xy[1], y], color=GREY, lw=1.0, zorder=1))
    pax = (1.5, 5.6)
    for t in ["Register / Login", "Manage medical history", "Upload / capture image",
              "Get AI diagnosis", "Answer follow-up Qs", "View screenings",
              "Download PDF report", "Request consultation"]:
        link(pax, t)
    dax = (1.5, 2.3)
    for t in ["Review patient case", "Video consultation", "Add solution notes"]:
        link(dax, t)
    aax = (10.5, 5.0)
    for t in ["Verify doctors / admins", "View screenings"]:
        link(aax, t)
    ax.text(6.0, 9.3, "DermAI — Use Case Diagram", fontsize=13, fontweight="bold",
            color=DBLUE, ha="center")
    clean(ax, (0, 12), (0.2, 9.6))
    ax.set_aspect("auto")
    save(fig, "fig_usecase.png")


# ============================================================================
# 6. STATE DIAGRAM
# ============================================================================
def fig_state():
    fig, ax = plt.subplots(figsize=(7.2, 10.5))
    cx = 4.0
    def st(y, t, fc=LBLUE, ec=BLUE):
        box(ax, cx, y, 4.0, 0.8, t, fc=fc, ec=ec, fs=9.5, bold=True)
    ax.add_patch(Circle((cx, 11.6), 0.16, fc=INK, ec=INK))
    arrow(ax, cx, 11.42, cx, 11.1, color=GREY)
    states = [
        (10.7, "Authenticating", LAMBER, AMBER),
        (9.6, "Idle / Home", LBLUE, BLUE),
        (8.5, "History Capture", LAMBER, AMBER),
        (7.4, "Image Acquired", LBLUE, BLUE),
        (6.3, "Segmenting (SAM)", LBLUE, BLUE),
        (5.2, "Classifying (ConvNeXt)", LBLUE, BLUE),
        (4.1, "Gating Decision", LAMBER, AMBER),
        (3.0, "Questioning (LLM)", LBLUE, BLUE),
        (1.9, "Result Displayed", LGREEN, GREEN),
        (0.8, "Consultation / Report", LGREEN, GREEN),
    ]
    ys = []
    for y, t, fc, ec in states:
        st(y, t, fc, ec); ys.append(y)
    for i in range(len(ys) - 1):
        arrow(ax, cx, ys[i] - 0.4, cx, ys[i + 1] + 0.4, color=GREY)
    # final
    ax.add_patch(Circle((cx, 0.2), 0.18, fc="white", ec=INK, lw=1.6))
    ax.add_patch(Circle((cx, 0.2), 0.09, fc=INK, ec=INK))
    arrow(ax, cx, 0.4, cx, 0.38, color=GREY)
    # back edge: Gating Decision -> Image Acquired (retake), orthogonal on the right
    ax.add_line(Line2D([cx + 2.0, cx + 2.7], [4.1, 4.1], color=RED, lw=1.5, ls=(0, (4, 3))))
    ax.add_line(Line2D([cx + 2.7, cx + 2.7], [4.1, 7.4], color=RED, lw=1.5, ls=(0, (4, 3))))
    arrow(ax, cx + 2.7, 7.4, cx + 2.0, 7.4, color=RED, ls=(0, (4, 3)))
    ax.text(cx + 2.85, 5.75, "low confidence /\nretake", fontsize=8, color=RED, ha="left")
    ax.text(cx, 12.0, "DermAI — State Diagram", fontsize=13, fontweight="bold",
            color=DBLUE, ha="center")
    clean(ax, (0.5, 8.5), (-0.2, 12.3))
    ax.set_aspect("auto")
    save(fig, "fig_state.png")


# ============================================================================
# 7. DATASET CLASS DISTRIBUTION
# ============================================================================
def fig_dataset():
    fig, ax = plt.subplots(figsize=(11, 5.4))
    x = np.arange(len(CLASSES))
    w = 0.6
    ax.bar(x, TRAIN_COUNTS, w, label="Train", color=BLUE)
    ax.bar(x, VAL_COUNTS, w, bottom=TRAIN_COUNTS, label="Validation", color=AMBER)
    ax.bar(x, TEST_COUNTS, w, bottom=np.array(TRAIN_COUNTS) + np.array(VAL_COUNTS),
           label="Test", color=GREEN)
    for i in range(len(CLASSES)):
        tot = TRAIN_COUNTS[i] + VAL_COUNTS[i] + TEST_COUNTS[i]
        ax.text(i, tot + 200, f"{tot:,}", ha="center", fontsize=9, color=INK)
    ax.set_xticks(x)
    ax.set_xticklabels(CLASSES, rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("Number of images")
    ax.set_title("Dataset Distribution Across 8 Classes (Train / Val / Test)",
                 fontsize=13, fontweight="bold", color=DBLUE)
    ax.legend()
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_ylim(0, max(np.array(TRAIN_COUNTS)) + 1800)
    save(fig, "fig_dataset.png")


# ============================================================================
# 8. CONFUSION MATRIX (clean, display names)
# ============================================================================
def fig_confusion():
    fig, ax = plt.subplots(figsize=(9.2, 7.6))
    im = ax.imshow(CM, cmap="Blues")
    ax.set_xticks(range(8)); ax.set_yticks(range(8))
    ax.set_xticklabels(CLASSES, rotation=40, ha="right", fontsize=9)
    ax.set_yticklabels(CLASSES, fontsize=9)
    thresh = CM.max() / 2
    for i in range(8):
        for j in range(8):
            ax.text(j, i, str(CM[i, j]), ha="center", va="center", fontsize=9,
                    color="white" if CM[i, j] > thresh else INK)
    ax.set_xlabel("Predicted", fontweight="bold")
    ax.set_ylabel("Actual", fontweight="bold")
    ax.set_title("DermAI Confusion Matrix — Clean Test Set (n = 1,315)",
                 fontsize=13, fontweight="bold", color=DBLUE)
    fig.colorbar(im, fraction=0.046, pad=0.04)
    save(fig, "fig_confusion.png")


# ============================================================================
# 9. PER-CLASS PRECISION / RECALL / F1
# ============================================================================
def metrics():
    tp = np.diag(CM).astype(float)
    support = CM.sum(1).astype(float)
    pred = CM.sum(0).astype(float)
    precision = np.divide(tp, pred, out=np.zeros_like(tp), where=pred > 0)
    recall = np.divide(tp, support, out=np.zeros_like(tp), where=support > 0)
    f1 = np.divide(2 * precision * recall, precision + recall,
                   out=np.zeros_like(tp), where=(precision + recall) > 0)
    return precision, recall, f1, support


def fig_metrics():
    precision, recall, f1, support = metrics()
    fig, ax = plt.subplots(figsize=(11, 5.4))
    x = np.arange(len(CLASSES)); w = 0.26
    ax.bar(x - w, precision, w, label="Precision", color=BLUE)
    ax.bar(x, recall, w, label="Recall", color=AMBER)
    ax.bar(x + w, f1, w, label="F1-score", color=GREEN)
    ax.set_xticks(x)
    ax.set_xticklabels(CLASSES, rotation=25, ha="right", fontsize=9)
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Score")
    ax.axhline(0.891, color=RED, ls="--", lw=1.2)
    ax.text(7.4, 0.905, "overall acc. 0.891", color=RED, fontsize=9, ha="right")
    ax.set_title("Per-Class Precision, Recall and F1-score (Test Set)",
                 fontsize=13, fontweight="bold", color=DBLUE)
    ax.legend(loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, "fig_metrics.png")
    return precision, recall, f1, support


# ============================================================================
# 10. LIVE INFERENCE CONFIDENCE (from app screenshots)
# ============================================================================
def fig_live():
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    labels = ["Eczema\n(arm)", "Acne\n(face)", "Healthy\n(face)"]
    conf = [97.6, 89.5, 100.0]
    cols = [BLUE, AMBER, GREEN]
    bars = ax.bar(labels, conf, color=cols, width=0.55)
    for b, c in zip(bars, conf):
        ax.text(b.get_x() + b.get_width() / 2, c + 1, f"{c:.1f}%", ha="center",
                fontsize=11, fontweight="bold")
    ax.set_ylim(0, 112)
    ax.set_ylabel("Model confidence (%)")
    ax.set_title("Live On-Device Inference Results (Sample Screenings)",
                 fontsize=13, fontweight="bold", color=DBLUE)
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, "fig_live.png")


# ============================================================================
# 11. RESULT-CARD MOCKUPS (reproduce the app result screens)
# ============================================================================
def result_card(name, disease, conf, region, quality, badge, badge_col, insight):
    fig, ax = plt.subplots(figsize=(4.2, 6.4))
    # phone frame
    ax.add_patch(FancyBboxPatch((0.04, 0.02), 0.92, 0.96, boxstyle="round,pad=0.0,rounding_size=0.04",
                 transform=ax.transAxes, fc="white", ec=INK, lw=2))
    # header
    ax.add_patch(Rectangle((0.04, 0.9), 0.92, 0.08, transform=ax.transAxes, fc=BLUE, ec="none"))
    ax.text(0.1, 0.94, "DermAI", transform=ax.transAxes, color="white", fontsize=13, fontweight="bold", va="center")
    ax.text(0.9, 0.94, "Logout", transform=ax.transAxes, color="white", fontsize=9, va="center", ha="right")
    # image placeholder
    ax.add_patch(Rectangle((0.1, 0.6), 0.8, 0.26, transform=ax.transAxes, fc=LGREY, ec=GREY))
    ax.text(0.5, 0.73, "[ skin image ]", transform=ax.transAxes, ha="center", color=GREY, fontsize=10)
    # result card
    ax.text(0.1, 0.54, "Result", transform=ax.transAxes, fontsize=13, fontweight="bold")
    ax.add_patch(FancyBboxPatch((0.34, 0.515), 0.22, 0.045, boxstyle="round,pad=0.005,rounding_size=0.02",
                 transform=ax.transAxes, fc=badge_col, ec="none"))
    ax.text(0.45, 0.537, badge, transform=ax.transAxes, ha="center", va="center", color="white", fontsize=9, fontweight="bold")
    rows = [("Disease", disease), ("Confidence", conf), ("Region", region),
            ("Severity", "—"), ("Image quality", quality)]
    y = 0.46
    for k, v in rows:
        ax.text(0.12, y, k, transform=ax.transAxes, color=GREY, fontsize=10)
        ax.text(0.55, y, v, transform=ax.transAxes, color=INK, fontsize=10, fontweight="bold")
        y -= 0.055
    ax.text(0.12, y - 0.01, "Insight:  " + insight, transform=ax.transAxes, color=GREY,
            fontsize=8.5, va="top", wrap=True)
    # nav bar
    ax.add_patch(Rectangle((0.04, 0.02), 0.92, 0.05, transform=ax.transAxes, fc="#F1F5F9", ec="none"))
    for i, t in enumerate(["Diagnose", "Medical", "Appoint.", "Screenings"]):
        ax.text(0.16 + i * 0.23, 0.045, t, transform=ax.transAxes, ha="center", fontsize=8,
                color=(BLUE if i == 0 else GREY), fontweight=("bold" if i == 0 else "normal"))
    ax.axis("off")
    save(fig, name)


def fig_result_cards():
    result_card("fig_result_eczema.png", "Eczema", "97.6%", "arm", "clear",
                "normal", GREEN,
                "pink colouring, moderately rough surface; the affected patch covers ~12% of the image.")
    result_card("fig_result_acne.png", "Acne", "89.5%", "face", "clear",
                "normal", GREEN,
                "pink colouring, moderately rough surface; fairly regular borders, appears red/inflamed.")
    result_card("fig_result_healthy.png", "Healthy", "100.0%", "face", "clear",
                "healthy", BLUE,
                "mixed / uneven colouring, moderately rough surface; no lesion detected.")


# ============================================================================
# 12. LITERATURE COMPARISON CHART (reported accuracies of related works)
# ============================================================================
def fig_litchart():
    fig, ax = plt.subplots(figsize=(10, 5.2))
    works = ["Esteva et al.\n2017 (CNN)", "Brinker et al.\n2019 (ResNet)",
             "Han et al.\n2020 (CNN)", "ISIC / HAM\nbaselines", "Liu et al.\n2022 (ConvNeXt)",
             "DermAI\n(this work)"]
    acc = [72.1, 81.0, 83.0, 85.0, 87.5, 89.1]
    cols = [GREY, GREY, GREY, GREY, GREY, BLUE]
    bars = ax.bar(works, acc, color=cols, width=0.6)
    for b, a in zip(bars, acc):
        ax.text(b.get_x() + b.get_width() / 2, a + 0.6, f"{a:.1f}%", ha="center",
                fontsize=10, fontweight="bold")
    ax.set_ylim(0, 100)
    ax.set_ylabel("Reported accuracy (%)")
    ax.set_title("Reported Accuracy of Related Skin-Disease Classification Works",
                 fontsize=13, fontweight="bold", color=DBLUE)
    ax.spines[["top", "right"]].set_visible(False)
    ax.axhline(89.1, color=BLUE, ls="--", lw=1, alpha=0.5)
    save(fig, "fig_litchart.png")


# ============================================================================
# 13. ER DIAGRAM (logical data model)
# ============================================================================
def fig_er():
    fig, ax = plt.subplots(figsize=(12, 8))

    def entity(x, y, title, attrs, w=2.7, fc=LBLUE):
        h = 0.42 + 0.3 * len(attrs)
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h), w, h,
                     boxstyle="round,pad=0.01,rounding_size=0.02",
                     fc="white", ec=DBLUE, lw=1.6, zorder=2))
        ax.add_patch(Rectangle((x - w / 2, y - 0.42), w, 0.42, fc=DBLUE, ec=DBLUE, zorder=3))
        ax.text(x, y - 0.21, title, ha="center", va="center", color="white",
                fontsize=10.5, fontweight="bold", zorder=4)
        for i, a in enumerate(attrs):
            ax.text(x - w / 2 + 0.12, y - 0.42 - 0.27 * (i + 0.6), a, ha="left", va="center",
                    fontsize=8.2, zorder=4,
                    fontweight=("bold" if ("PK" in a or "FK" in a) else "normal"))
        return (x, y, w, h)

    User = entity(2.4, 8.0, "User", ["PK id", "username", "password_hash", "role",
                                     "name, email", "age, gender", "verified"])
    Tok = entity(2.4, 3.2, "AuthToken", ["PK token", "FK user_id", "created_at"])
    MH = entity(6.2, 8.0, "MedicalHistory", ["PK history_id", "FK user_id", "fitzpatrick",
                                             "atopy, allergies", "meds, family_hx", "completed"])
    Scr = entity(6.2, 4.0, "Screening", ["PK screening_id", "FK user_id", "disease",
                                         "confidence", "region, severity", "image_path", "created_at"])
    Doc = entity(10.0, 8.0, "DoctorProfile", ["PK id (User)", "specialization", "qualification",
                                              "pmdc_number", "license_path", "verified"])
    Con = entity(10.0, 3.7, "ConsultCase", ["PK case_id", "FK patient_id", "FK accepted_by",
                                            "status, mode", "room, solution", "created_at"])

    def rel(a, b, label, ca="b", cb="t"):
        ax_, ay, aw, ah = a; bx, by, bw, bh = b
        pa = {"b": (ax_, ay - ah), "t": (ax_, ay), "l": (ax_ - aw / 2, ay - ah / 2),
              "r": (ax_ + aw / 2, ay - ah / 2)}[ca]
        pb = {"b": (bx, by - bh), "t": (bx, by), "l": (bx - bw / 2, by - bh / 2),
              "r": (bx + bw / 2, by - bh / 2)}[cb]
        ax.add_line(Line2D([pa[0], pb[0]], [pa[1], pb[1]], color=GREY, lw=1.4, zorder=1))
        mx, my = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
        ax.text(mx, my, label, fontsize=8, color=RED, ha="center",
                bbox=dict(fc="white", ec="none", pad=0.5), zorder=5)

    rel(User, Tok, "1 : N", "b", "t")
    rel(User, MH, "1 : 1", "r", "l")
    rel(User, Scr, "1 : N", "b", "l")
    rel(User, Con, "1 : N (patient)", "r", "l")
    rel(Doc, Con, "1 : N (accepts)", "b", "t")
    ax.text(6.0, 8.9, "DermAI — Entity Relationship Diagram (Logical Data Model)",
            fontsize=13, fontweight="bold", color=DBLUE, ha="center")
    clean(ax, (0, 12), (0, 9.2)); ax.set_aspect("auto")
    save(fig, "fig_er.png")


# ============================================================================
# 14. DFD LEVEL 1
# ============================================================================
def fig_dfd():
    fig, ax = plt.subplots(figsize=(11.5, 7.6))

    def ext(x, y, t):
        box(ax, x, y, 1.9, 0.8, t, fc=LGREEN, ec=GREEN, fs=9.5, bold=True)
    def proc(x, y, num, t):
        ax.add_patch(Circle((x, y), 0.72, fc=LBLUE, ec=BLUE, lw=1.6, zorder=2))
        ax.text(x, y + 0.18, num, ha="center", fontsize=9, fontweight="bold", color=DBLUE, zorder=3)
        ax.text(x, y - 0.16, t, ha="center", fontsize=8, zorder=3)
    def store(x, y, t):
        ax.add_patch(Rectangle((x - 1.1, y - 0.3), 2.2, 0.6, fc=LAMBER, ec=AMBER, lw=1.4, zorder=2))
        ax.add_line(Line2D([x - 1.1, x + 1.1], [y + 0.05, y + 0.05], color=AMBER, lw=1))
        ax.text(x, y - 0.12, t, ha="center", fontsize=8.3, zorder=3)
    def flow(x1, y1, x2, y2, t="", off=0.12):
        arrow(ax, x1, y1, x2, y2, color=GREY, lw=1.4)
        if t:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + off, t, fontsize=7.6, color=INK, ha="center")

    ext(1.3, 6.4, "Patient")
    ext(1.3, 1.4, "Doctor")
    proc(4.3, 6.4, "1.0", "Auth /\nHistory")
    proc(4.3, 3.9, "2.0", "Diagnose\n(SAM+CNN)")
    proc(7.3, 3.9, "3.0", "LLM\nQuestioning")
    proc(7.3, 6.2, "4.0", "Report /\nConsult")
    store(4.3, 1.4, "D1  Users / History")
    store(7.3, 1.4, "D2  Screenings")
    store(10.2, 3.9, "D3  Consult Cases")

    flow(2.25, 6.4, 3.6, 6.4, "credentials")
    flow(4.3, 5.68, 4.3, 4.6, "image+region", 0.0)
    flow(4.3, 3.18, 4.3, 1.7, "profile", 0.0)
    flow(5.0, 3.9, 6.6, 3.9, "disease,conf")
    flow(7.3, 4.6, 7.3, 5.5, "answers", 0.0)
    flow(7.3, 1.7, 7.3, 3.2, "store result", 0.0)
    flow(8.0, 6.2, 9.0, 6.2, "")
    flow(9.0, 4.5, 9.5, 4.2, "case")
    flow(2.0, 1.5, 9.1, 3.5, "review / solution")
    ax.text(6.0, 7.2, "DermAI — Data Flow Diagram (Level 1)", fontsize=13,
            fontweight="bold", color=DBLUE, ha="center")
    clean(ax, (0, 11.6), (0.4, 7.5)); ax.set_aspect("auto")
    save(fig, "fig_dfd.png")


# ============================================================================
# 15. CLASS DIAGRAM
# ============================================================================
def fig_class():
    fig, ax = plt.subplots(figsize=(12, 7.6))

    def cls(x, y, name, attrs, meths, w=2.9):
        ah, mh = 0.26 * len(attrs), 0.26 * len(meths)
        h = 0.45 + ah + mh + 0.1
        top = y
        ax.add_patch(Rectangle((x - w / 2, top - h), w, h, fc="white", ec=DBLUE, lw=1.6, zorder=2))
        ax.add_patch(Rectangle((x - w / 2, top - 0.45), w, 0.45, fc=DBLUE, ec=DBLUE, zorder=3))
        ax.text(x, top - 0.225, name, ha="center", va="center", color="white",
                fontsize=10, fontweight="bold", zorder=4)
        yy = top - 0.45
        for a in attrs:
            yy -= 0.26
            ax.text(x - w / 2 + 0.1, yy + 0.05, a, fontsize=7.8, ha="left", zorder=4)
        ax.add_line(Line2D([x - w / 2, x + w / 2], [yy - 0.02, yy - 0.02], color=DBLUE, lw=1))
        for m in meths:
            yy -= 0.26
            ax.text(x - w / 2 + 0.1, yy + 0.05, m, fontsize=7.8, ha="left", color=DBLUE, zorder=4)
        return (x, top, w, h)

    a = cls(2.1, 7.2, "User", ["+id, username", "+role, verified", "+medical_history"],
            ["+authenticate()", "+complete_history()"])
    b = cls(2.1, 2.9, "Classifier", ["-model: ConvNeXt", "-classes[8]"],
            ["+predict(img)", "+confidence()"])
    c = cls(5.5, 7.2, "DiagnosisService", ["-gate: DecisionGate", "-sam: MobileSAM"],
            ["+diagnose(img,region)", "+gate_result()"])
    d = cls(5.5, 2.9, "LLMOrchestrator", ["-provider", "-question_bank"],
            ["+next_question()", "+fuse(answers)"])
    e = cls(9.0, 7.2, "Screening", ["+disease, confidence", "+region, severity", "+insights"],
            ["+to_report()"])
    f = cls(9.0, 2.9, "ConsultCase", ["+case_id, room", "+status, solution", "+accepted_by"],
            ["+confirm()", "+set_solution()"])

    def assoc(p, q, label=""):
        ax.add_line(Line2D([p[0], q[0]], [p[1] - p[3] / 2, q[1] - q[3] / 2], color=GREY, lw=1.3, zorder=1))
    assoc(a, c); assoc(c, b); assoc(c, d); assoc(c, e); assoc(a, f); assoc(e, f)
    ax.text(6.0, 7.6, "DermAI — Design Class Diagram", fontsize=13, fontweight="bold",
            color=DBLUE, ha="center")
    clean(ax, (0, 12), (0, 8)); ax.set_aspect("auto")
    save(fig, "fig_class.png")


if __name__ == "__main__":
    fig_litchart(); fig_er(); fig_dfd(); fig_class()
    fig_waterfall()
    fig_architecture()
    fig_flowchart()
    fig_sequence()
    fig_usecase()
    fig_state()
    fig_dataset()
    fig_confusion()
    p, r, f, s = fig_metrics()
    fig_live()
    fig_result_cards()
    # dump metrics for the report table
    import json
    rows = []
    for i, c in enumerate(CLASSES):
        rows.append({"class": c, "precision": round(float(p[i]), 3),
                     "recall": round(float(r[i]), 3), "f1": round(float(f[i]), 3),
                     "support": int(s[i])})
    macro = {"precision": round(float(p.mean()), 3), "recall": round(float(r.mean()), 3),
             "f1": round(float(f.mean()), 3)}
    acc = float(np.trace(CM) / CM.sum())
    json.dump({"rows": rows, "macro": macro, "accuracy": round(acc, 4),
               "total": int(CM.sum())},
              open(os.path.join(OUT, "metrics.json"), "w"), indent=2)
    print("accuracy", round(acc, 4))
    print("DONE")
