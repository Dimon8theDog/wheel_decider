#!/usr/bin/env python3
"""Wheel Solver GUI - Interactive bonus wheel configuration tool.

Type a bonus cost, adjust the reward spread, click Generate, get a complete
wheel with rewards and probabilities.

Usage:
    python wheel_gui.py
"""

import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wheel_solver import solve_wheel_precise


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FS_RATE = 0.20
MAX_FS = 200
MAX_FS_EUR = MAX_FS * FS_RATE   # €40

HB_FS_RATE = 0.50
MAX_HB_FS = 100
MAX_HB_FS_EUR = MAX_HB_FS * HB_FS_RATE   # €50

NICE_FS = [5, 10, 15, 20, 25, 50, 75, 100, 125, 150, 175, 200]
NICE_HB_FS = [5, 10, 15, 20, 25, 50, 75, 100]

MIN_SECTORS = 3
MAX_SECTORS = 12
DEFAULT_NUM_SECTORS = 6
DEFAULT_SPREAD = 5
DEFAULT_DISABLED = 1


# ---------------------------------------------------------------------------
# Translations
# ---------------------------------------------------------------------------
STRINGS = {
    "en": {
        "title": "Wheel Solver",
        "subtitle": "Enter a bonus cost, adjust the spread, click Generate.",
        "bonus_cost": "Bonus cost (\u20ac):",
        "sectors": "Sectors:",
        "disabled": "Disabled:",
        "in_spread": "In spread",
        "undershoot": "Undershoot:",
        "pct_sep": "% \u2013",
        "pct_end": "%",
        "spread_label": "Reward spread:",
        "tight": "Tight",
        "wide": "Wide",
        "generate": "Generate Wheel",
        "recalculate": "Recalculate Probs",
        "export": "Export CSV",
        "col_num": "#",
        "col_reward": "Reward",
        "col_value": "EUR Value",
        "col_dis": "Dis.",
        "col_prob": "Prob %",
        "col_ev": "EV Contrib",
        "col_cum": "Cum. EV",
        "cheat1": "FS = Free Spins (\u20ac0.20/spin)  \u2022  HB FS = High Bet Free Spins (\u20ac0.50/spin)  \u2022  Dis. = visible on wheel but unwinnable (0%)",
        "cheat2": "Undershoot = target margin below bonus cost  \u2022  EV = Expected Value (avg payout per player)  \u2022  Spread = reward value range",
        "cheat3": "Tip: Type rewards like \"50 FS\", \"25 HB FS\", or \"\u20ac30\" in the Reward column \u2014 EUR values auto-fill on Recalculate.",
        "err_input": "Bonus cost must be a positive number.",
        "err_bad_value": "Bad value in sector {}: '{}'",
        "err_min_sectors": "Need at least 2 sectors.",
        "err_invalid": "Invalid input values.",
        "err_no_solution": "No solution found",
        "err_undershoot": "Undershoot min must be < max.",
        "export_title": "Export CSV",
        "export_none": "No results yet. Generate a wheel first.",
        "export_done": "Saved to:\n{}",
        "lang_btn": "RU",
    },
    "ru": {
        "title": "\u041a\u043e\u043b\u0435\u0441\u043e \u0411\u043e\u043d\u0443\u0441\u043e\u0432",
        "subtitle": "\u0412\u0432\u0435\u0434\u0438\u0442\u0435 \u0441\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c \u0431\u043e\u043d\u0443\u0441\u0430, \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u0442\u0435 \u0440\u0430\u0437\u0431\u0440\u043e\u0441, \u043d\u0430\u0436\u043c\u0438\u0442\u0435 \u0413\u0435\u043d\u0435\u0440\u0438\u0440\u043e\u0432\u0430\u0442\u044c.",
        "bonus_cost": "\u0421\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c \u0431\u043e\u043d\u0443\u0441\u0430 (\u20ac):",
        "sectors": "\u0421\u0435\u043a\u0442\u043e\u0440\u044b:",
        "disabled": "\u041e\u0442\u043a\u043b.:",
        "in_spread": "\u0412 \u0440\u0430\u0437\u0431\u0440\u043e\u0441\u0435",
        "undershoot": "\u041d\u0435\u0434\u043e\u043b\u0451\u0442:",
        "pct_sep": "% \u2013",
        "pct_end": "%",
        "spread_label": "\u0420\u0430\u0437\u0431\u0440\u043e\u0441 \u043d\u0430\u0433\u0440\u0430\u0434:",
        "tight": "\u0423\u0437\u043a\u0438\u0439",
        "wide": "\u0428\u0438\u0440\u043e\u043a\u0438\u0439",
        "generate": "\u0413\u0435\u043d\u0435\u0440\u0438\u0440\u043e\u0432\u0430\u0442\u044c",
        "recalculate": "\u041f\u0435\u0440\u0435\u0441\u0447\u0438\u0442\u0430\u0442\u044c",
        "export": "\u042d\u043a\u0441\u043f\u043e\u0440\u0442 CSV",
        "col_num": "\u2116",
        "col_reward": "\u041d\u0430\u0433\u0440\u0430\u0434\u0430",
        "col_value": "EUR",
        "col_dis": "\u041e\u0442\u043a\u043b.",
        "col_prob": "\u0412\u0435\u0440. %",
        "col_ev": "\u0412\u043a\u043b\u0430\u0434 EV",
        "col_cum": "\u0421\u0443\u043c\u043c. EV",
        "cheat1": "FS = \u0424\u0440\u0438\u0441\u043f\u0438\u043d\u044b (\u20ac0.20/\u0441\u043f\u0438\u043d)  \u2022  HB FS = \u0424\u0440\u0438\u0441\u043f\u0438\u043d\u044b \u0432\u044b\u0441. \u0441\u0442\u0430\u0432\u043a\u0438 (\u20ac0.50/\u0441\u043f\u0438\u043d)  \u2022  \u041e\u0442\u043a\u043b. = \u0432\u0438\u0434\u043d\u043e, \u043d\u043e 0%",
        "cheat2": "\u041d\u0435\u0434\u043e\u043b\u0451\u0442 = \u043e\u0442\u0441\u0442\u0443\u043f \u043d\u0438\u0436\u0435 \u0441\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u0438 \u0431\u043e\u043d\u0443\u0441\u0430  \u2022  EV = \u041e\u0436\u0438\u0434\u0430\u0435\u043c\u0430\u044f \u0432\u044b\u043f\u043b\u0430\u0442\u0430 (\u0441\u0440\u0435\u0434\u043d\u0435\u0435)  \u2022  \u0420\u0430\u0437\u0431\u0440\u043e\u0441 = \u0448\u0438\u0440\u0438\u043d\u0430 \u0434\u0438\u0430\u043f\u0430\u0437\u043e\u043d\u0430",
        "cheat3": "\u0421\u043e\u0432\u0435\u0442: \u0412\u0432\u043e\u0434\u0438\u0442\u0435 \u043d\u0430\u0433\u0440\u0430\u0434\u044b \u043a\u0430\u043a \"50 FS\", \"25 HB FS\" \u0438\u043b\u0438 \"\u20ac30\" \u2014 \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u044f \u0440\u0430\u0441\u0441\u0447\u0438\u0442\u0430\u044e\u0442\u0441\u044f \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438.",
        "err_input": "\u0421\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c \u0431\u043e\u043d\u0443\u0441\u0430 \u0434\u043e\u043b\u0436\u043d\u0430 \u0431\u044b\u0442\u044c \u043f\u043e\u043b\u043e\u0436\u0438\u0442\u0435\u043b\u044c\u043d\u044b\u043c \u0447\u0438\u0441\u043b\u043e\u043c.",
        "err_bad_value": "\u041e\u0448\u0438\u0431\u043a\u0430 \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u044f \u0432 \u0441\u0435\u043a\u0442\u043e\u0440\u0435 {}: '{}'",
        "err_min_sectors": "\u041d\u0443\u0436\u043d\u043e \u043c\u0438\u043d\u0438\u043c\u0443\u043c 2 \u0441\u0435\u043a\u0442\u043e\u0440\u0430.",
        "err_invalid": "\u041d\u0435\u043a\u043e\u0440\u0440\u0435\u043a\u0442\u043d\u044b\u0435 \u0432\u0445\u043e\u0434\u043d\u044b\u0435 \u0434\u0430\u043d\u043d\u044b\u0435.",
        "err_no_solution": "\u0420\u0435\u0448\u0435\u043d\u0438\u0435 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u043e",
        "err_undershoot": "\u041c\u0438\u043d. \u043d\u0435\u0434\u043e\u043b\u0451\u0442 \u0434\u043e\u043b\u0436\u0435\u043d \u0431\u044b\u0442\u044c < \u043c\u0430\u043a\u0441.",
        "export_title": "\u042d\u043a\u0441\u043f\u043e\u0440\u0442 CSV",
        "export_none": "\u041d\u0435\u0442 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u043e\u0432. \u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0441\u0433\u0435\u043d\u0435\u0440\u0438\u0440\u0443\u0439\u0442\u0435 \u043a\u043e\u043b\u0435\u0441\u043e.",
        "export_done": "\u0421\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u043e \u0432:\n{}",
        "lang_btn": "EN",
    },
}


# ---------------------------------------------------------------------------
# Spread / ratio helpers
# ---------------------------------------------------------------------------
def _spread_to_ratios(spread):
    """Convert a spread value (1-10) to (min_ratio, max_ratio)."""
    t = max(0.0, min(1.0, (spread - 1) / 9))
    t = t ** 2
    min_r = 0.90 * (0.05 / 0.90) ** t
    max_r = 1.10 * (6.00 / 1.10) ** t
    return min_r, max_r


def _compute_ratios(num_sectors, min_ratio=0.20, max_ratio=3.0):
    """Log-spaced value-multiplier ratios for *num_sectors* sectors."""
    if num_sectors <= 0:
        return []
    if num_sectors == 1:
        return [min(1.0, max_ratio)]
    if max_ratio <= min_ratio:
        return [
            min_ratio + (max_ratio - min_ratio) * i / (num_sectors - 1)
            for i in range(num_sectors)
        ]
    return [
        min_ratio * (max_ratio / min_ratio) ** (i / (num_sectors - 1))
        for i in range(num_sectors)
    ]


# ---------------------------------------------------------------------------
# Reward label parsing
# ---------------------------------------------------------------------------
def parse_reward_label(label):
    """Parse a reward label like '50 FS', '25 HB FS', or '\u20ac30'.

    Returns the EUR value as a float, or None if unrecognised.
    """
    label = label.strip()
    if not label:
        return None
    # "25 HB FS" or "25 HBFS"
    m = re.match(r'^(\d+)\s*HB\s*FS$', label, re.IGNORECASE)
    if m:
        return int(m.group(1)) * HB_FS_RATE
    # "50 FS"
    m = re.match(r'^(\d+)\s*FS$', label, re.IGNORECASE)
    if m:
        return int(m.group(1)) * FS_RATE
    # "\u20ac30" or "EUR30" or "EUR 30"
    m = re.match(r'^[\u20acEUR]+\s*(\d+(?:\.\d+)?)$', label, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


# ---------------------------------------------------------------------------
# Snap candidates for auto-generation
# ---------------------------------------------------------------------------
def _snap_candidates(raw_eur):
    """All snap options across reward types, sorted by closeness to raw_eur."""
    candidates = []
    fs_bias = 0.30

    for fs in NICE_FS:
        val = fs * FS_RATE
        candidates.append((abs(val - raw_eur) + fs_bias, val, f"{fs} FS"))
    for fs in NICE_HB_FS:
        val = fs * HB_FS_RATE
        candidates.append((abs(val - raw_eur) + fs_bias, val, f"{fs} HB FS"))

    if raw_eur <= 50:
        step = 5
    elif raw_eur <= 200:
        step = 10
    elif raw_eur <= 500:
        step = 25
    else:
        step = 50
    base = max(round(raw_eur / step) * step, step)
    for offset in [0, -step, step, -2 * step, 2 * step]:
        eur = base + offset
        if eur >= step:
            candidates.append((abs(eur - raw_eur), float(eur),
                               f"\u20ac{int(eur)}"))

    candidates.sort(key=lambda x: x[0])
    return candidates


# ---------------------------------------------------------------------------
# Sector generation
# ---------------------------------------------------------------------------
def generate_sectors(target, num_sectors=DEFAULT_NUM_SECTORS,
                     spread=DEFAULT_SPREAD, num_disabled=DEFAULT_DISABLED,
                     disabled_in_spread=True):
    """Auto-generate sector rewards for a given bonus cost and spread."""
    min_ratio, max_ratio = _spread_to_ratios(spread)
    num_disabled = max(0, min(num_disabled, num_sectors - 1))
    num_active = num_sectors - num_disabled

    active_ratios = _compute_ratios(num_active, min_ratio, max_ratio)

    if num_disabled == 0:
        dis_ratios = []
    elif disabled_in_spread:
        dis_lo = active_ratios[-1] * 1.15 if active_ratios else max_ratio * 0.8
        dis_ratios = _compute_ratios(num_disabled, dis_lo, max_ratio) \
            if num_disabled > 1 else [max(dis_lo, max_ratio * 0.9)]
    else:
        dis_base = max_ratio * 1.4
        dis_ratios = [dis_base * (1.3 ** d) for d in range(num_disabled)]

    used_labels = set()
    sectors = []

    def _pick(ratio, disabled):
        candidates = _snap_candidates(target * ratio)
        for _, val, label in candidates:
            if label not in used_labels:
                used_labels.add(label)
                sectors.append({"label": label, "value": val,
                                "disabled": disabled})
                return
        # Fallback: use raw EUR value (bug fix — never skip a sector)
        raw = target * ratio
        val = round(raw, 2)
        label = f"\u20ac{val:.2f}"
        sectors.append({"label": label, "value": val, "disabled": disabled})

    for ratio in active_ratios:
        _pick(ratio, False)
    for ratio in dis_ratios:
        _pick(ratio, True)

    sectors.sort(key=lambda s: (s["value"], s["disabled"]))
    return sectors


# ---------------------------------------------------------------------------
# Colours / styling
# ---------------------------------------------------------------------------
BG = "#1e1e2e"
BG2 = "#262640"
BG_INPUT = "#32324a"
FG = "#dcdcec"
FG_DIM = "#8080a0"
ACCENT = "#7c6ff7"
ACCENT_HI = "#9a8fff"
GREEN = "#50c878"
RED = "#e05555"
BORDER = "#3a3a55"


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
class WheelSolverApp(tk.Tk):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self._lang = "en"
        self.title("Wheel Solver")
        self.configure(bg=BG)
        self.geometry("900x780")
        self.minsize(800, 620)

        self._i18n = {}  # key -> widget for language updates
        self._setup_styles()
        self._build_ui()

        self._target_var.set("65")
        self._generate()

    def _t(self, key):
        return STRINGS[self._lang].get(key, key)

    # ------------------------------------------------------------------
    # Styles
    # ------------------------------------------------------------------
    def _setup_styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=FG,
                     fieldbackground=BG_INPUT, bordercolor=BORDER,
                     troughcolor=BG2)
        s.configure("TLabel", background=BG, foreground=FG,
                     font=("Segoe UI", 10))
        s.configure("Title.TLabel", font=("Segoe UI", 14, "bold"),
                     foreground=ACCENT, background=BG)
        s.configure("Dim.TLabel", foreground=FG_DIM, background=BG,
                     font=("Segoe UI", 9))
        s.configure("Cheat.TLabel", foreground=FG_DIM, background=BG,
                     font=("Segoe UI", 8))
        s.configure("Result.TLabel", background=BG2, foreground=FG,
                     font=("Consolas", 10), padding=(6, 3))
        s.configure("Green.TLabel", foreground=GREEN, background=BG,
                     font=("Segoe UI", 11, "bold"))
        s.configure("Red.TLabel", foreground=RED, background=BG,
                     font=("Segoe UI", 10))
        s.configure("TEntry", fieldbackground=BG_INPUT, foreground=FG,
                     insertcolor=FG, padding=3)
        s.configure("TCheckbutton", background=BG, foreground=FG)
        s.configure("TFrame", background=BG)
        s.configure("Accent.TButton", background=ACCENT, foreground="#fff",
                     font=("Segoe UI", 11, "bold"), padding=(18, 8))
        s.map("Accent.TButton",
               background=[("active", ACCENT_HI), ("pressed", ACCENT)])
        s.configure("TButton", background=BG2, foreground=FG,
                     font=("Segoe UI", 9), padding=(10, 5))
        s.map("TButton", background=[("active", BG_INPUT)])
        s.configure("Lang.TButton", background=BG2, foreground=ACCENT,
                     font=("Segoe UI", 9, "bold"), padding=(8, 3))
        s.map("Lang.TButton", background=[("active", BG_INPUT)])
        s.configure("TSpinbox", fieldbackground=BG_INPUT, foreground=FG,
                     padding=3)

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        pad = dict(padx=18, pady=4)

        # -- Title row with language toggle --
        title_frame = ttk.Frame(self)
        title_frame.pack(fill=tk.X, padx=18, pady=(14, 0))

        lbl_title = ttk.Label(title_frame, text=self._t("title"),
                              style="Title.TLabel")
        lbl_title.pack(side=tk.LEFT)
        self._i18n["title"] = lbl_title

        self._lang_btn = ttk.Button(title_frame, text=self._t("lang_btn"),
                                    style="Lang.TButton",
                                    command=self._toggle_language)
        self._lang_btn.pack(side=tk.RIGHT)

        lbl_sub = ttk.Label(self, text=self._t("subtitle"),
                            style="Dim.TLabel")
        lbl_sub.pack(anchor=tk.W, padx=18, pady=(0, 8))
        self._i18n["subtitle"] = lbl_sub

        # -- Input row 1 --
        inp = ttk.Frame(self)
        inp.pack(fill=tk.X, **pad)

        lbl_bc = ttk.Label(inp, text=self._t("bonus_cost"))
        lbl_bc.pack(side=tk.LEFT)
        self._i18n["bonus_cost"] = lbl_bc

        self._target_var = tk.StringVar()
        te = ttk.Entry(inp, textvariable=self._target_var, width=8,
                        font=("Segoe UI", 12))
        te.pack(side=tk.LEFT, padx=(6, 16))
        te.bind("<Return>", lambda e: self._generate())

        lbl_sec = ttk.Label(inp, text=self._t("sectors"))
        lbl_sec.pack(side=tk.LEFT)
        self._i18n["sectors"] = lbl_sec

        self._num_sectors_var = tk.IntVar(value=DEFAULT_NUM_SECTORS)
        sb = ttk.Spinbox(inp, from_=MIN_SECTORS, to=MAX_SECTORS,
                          textvariable=self._num_sectors_var, width=4,
                          font=("Segoe UI", 10),
                          command=self._on_sector_count_change)
        sb.pack(side=tk.LEFT, padx=(4, 16))
        sb.bind("<Return>", lambda e: self._on_sector_count_change())

        lbl_dis = ttk.Label(inp, text=self._t("disabled"))
        lbl_dis.pack(side=tk.LEFT)
        self._i18n["disabled"] = lbl_dis

        self._num_disabled_var = tk.IntVar(value=DEFAULT_DISABLED)
        sb_dis = ttk.Spinbox(inp, from_=0, to=MAX_SECTORS - 1,
                              textvariable=self._num_disabled_var, width=4,
                              font=("Segoe UI", 10))
        sb_dis.pack(side=tk.LEFT, padx=(4, 4))

        self._dis_in_spread_var = tk.BooleanVar(value=True)
        self._cb_inspread = ttk.Checkbutton(inp, text=self._t("in_spread"),
                                            variable=self._dis_in_spread_var)
        self._cb_inspread.pack(side=tk.LEFT, padx=(0, 16))
        self._i18n["in_spread"] = self._cb_inspread

        lbl_us = ttk.Label(inp, text=self._t("undershoot"))
        lbl_us.pack(side=tk.LEFT)
        self._i18n["undershoot"] = lbl_us

        self._usmin_var = tk.StringVar(value="5")
        ttk.Entry(inp, textvariable=self._usmin_var, width=4).pack(
            side=tk.LEFT, padx=(4, 0))
        lbl_pct = ttk.Label(inp, text=self._t("pct_sep"))
        lbl_pct.pack(side=tk.LEFT, padx=2)
        self._i18n["pct_sep"] = lbl_pct

        self._usmax_var = tk.StringVar(value="8")
        ttk.Entry(inp, textvariable=self._usmax_var, width=4).pack(
            side=tk.LEFT, padx=(0, 4))
        lbl_pct2 = ttk.Label(inp, text=self._t("pct_end"))
        lbl_pct2.pack(side=tk.LEFT)
        self._i18n["pct_end"] = lbl_pct2

        # -- Input row 2: spread slider --
        slider_frame = ttk.Frame(self)
        slider_frame.pack(fill=tk.X, padx=18, pady=(2, 6))

        lbl_sp = ttk.Label(slider_frame, text=self._t("spread_label"))
        lbl_sp.pack(side=tk.LEFT)
        self._i18n["spread_label"] = lbl_sp

        self._lbl_tight = ttk.Label(slider_frame, text=self._t("tight"),
                                    style="Dim.TLabel")
        self._lbl_tight.pack(side=tk.LEFT, padx=(8, 0))
        self._i18n["tight"] = self._lbl_tight

        self._spread_var = tk.IntVar(value=DEFAULT_SPREAD)
        self._spread_scale = tk.Scale(
            slider_frame, from_=1, to=10, orient=tk.HORIZONTAL,
            variable=self._spread_var, bg=BG, fg=FG,
            troughcolor=BG_INPUT, highlightthickness=0,
            sliderrelief=tk.FLAT, activebackground=ACCENT_HI,
            font=("Segoe UI", 9), showvalue=True, length=280)
        self._spread_scale.pack(side=tk.LEFT, padx=4)

        self._lbl_wide = ttk.Label(slider_frame, text=self._t("wide"),
                                   style="Dim.TLabel")
        self._lbl_wide.pack(side=tk.LEFT, padx=(0, 12))
        self._i18n["wide"] = self._lbl_wide

        self._spread_desc_var = tk.StringVar()
        ttk.Label(slider_frame, textvariable=self._spread_desc_var,
                  style="Dim.TLabel").pack(side=tk.LEFT)
        self._update_spread_desc()
        self._spread_var.trace_add("write",
                                   lambda *_: self._update_spread_desc())

        # -- Buttons --
        btn = ttk.Frame(self)
        btn.pack(fill=tk.X, **pad)
        self._btn_gen = ttk.Button(btn, text=self._t("generate"),
                                   style="Accent.TButton",
                                   command=self._generate)
        self._btn_gen.pack(side=tk.LEFT, padx=(0, 10))
        self._btn_recalc = ttk.Button(btn, text=self._t("recalculate"),
                                      command=self._recalculate)
        self._btn_recalc.pack(side=tk.LEFT, padx=(0, 10))
        self._btn_export = ttk.Button(btn, text=self._t("export"),
                                      command=self._export_csv)
        self._btn_export.pack(side=tk.LEFT)

        # -- Sector table --
        tbl_outer = ttk.Frame(self)
        tbl_outer.pack(fill=tk.BOTH, expand=True, padx=18, pady=(8, 0))
        self._tbl = ttk.Frame(tbl_outer)
        self._tbl.pack(fill=tk.BOTH, expand=True)

        self._header_keys = ["col_num", "col_reward", "col_value",
                             "col_dis", "col_prob", "col_ev", "col_cum"]
        self._header_labels = []
        for j, key in enumerate(self._header_keys):
            lbl = ttk.Label(self._tbl, text=self._t(key),
                            style="Dim.TLabel", anchor=tk.CENTER)
            lbl.grid(row=0, column=j, padx=4, pady=(0, 2), sticky=tk.EW)
            self._header_labels.append(lbl)

        ttk.Separator(self._tbl, orient=tk.HORIZONTAL).grid(
            row=1, column=0, columnspan=len(self._header_keys),
            sticky=tk.EW, pady=2)
        for j in range(len(self._header_keys)):
            self._tbl.columnconfigure(j, weight=1)

        self._sector_rows = []
        for i in range(MAX_SECTORS):
            self._sector_rows.append(
                self._make_sector_row(self._tbl, i, row_offset=2))
        self._show_rows(DEFAULT_NUM_SECTORS)

        # -- Summary --
        self._summary_var = tk.StringVar()
        self._summary_lbl = ttk.Label(self, textvariable=self._summary_var,
                                       style="Green.TLabel")
        self._summary_lbl.pack(anchor=tk.W, padx=22, pady=(8, 0))

        self._detail_var = tk.StringVar()
        ttk.Label(self, textvariable=self._detail_var,
                  style="Dim.TLabel").pack(anchor=tk.W, padx=22, pady=(2, 6))

        # -- Cheat sheet --
        cs = ttk.Frame(self)
        cs.pack(fill=tk.X, padx=18, pady=(2, 10))
        ttk.Separator(cs, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 6))
        self._cheat1 = ttk.Label(cs, text=self._t("cheat1"),
                                 style="Cheat.TLabel")
        self._cheat1.pack(anchor=tk.W)
        self._cheat2 = ttk.Label(cs, text=self._t("cheat2"),
                                 style="Cheat.TLabel")
        self._cheat2.pack(anchor=tk.W)
        self._cheat3 = ttk.Label(cs, text=self._t("cheat3"),
                                 style="Cheat.TLabel")
        self._cheat3.pack(anchor=tk.W)

        self._last_result = None

    # ------------------------------------------------------------------
    # Language toggle
    # ------------------------------------------------------------------
    def _toggle_language(self):
        self._lang = "ru" if self._lang == "en" else "en"
        self._apply_language()

    def _apply_language(self):
        t = self._t
        # Title / subtitle
        self._i18n["title"].configure(text=t("title"))
        self._i18n["subtitle"].configure(text=t("subtitle"))
        self._lang_btn.configure(text=t("lang_btn"))
        # Input row
        for key in ("bonus_cost", "sectors", "disabled", "undershoot",
                     "pct_sep", "pct_end", "spread_label", "tight", "wide"):
            self._i18n[key].configure(text=t(key))
        self._cb_inspread.configure(text=t("in_spread"))
        # Buttons
        self._btn_gen.configure(text=t("generate"))
        self._btn_recalc.configure(text=t("recalculate"))
        self._btn_export.configure(text=t("export"))
        # Column headers
        for lbl, key in zip(self._header_labels, self._header_keys):
            lbl.configure(text=t(key))
        # Cheat sheet
        self._cheat1.configure(text=t("cheat1"))
        self._cheat2.configure(text=t("cheat2"))
        self._cheat3.configure(text=t("cheat3"))
        # Spread desc
        self._update_spread_desc()

    # ------------------------------------------------------------------
    # Spread description
    # ------------------------------------------------------------------
    def _update_spread_desc(self):
        try:
            spread = self._spread_var.get()
            target = float(self._target_var.get())
        except (tk.TclError, ValueError):
            self._spread_desc_var.set("")
            return
        min_r, max_r = _spread_to_ratios(spread)
        lo = target * min_r
        hi = target * max_r
        self._spread_desc_var.set(
            f"Active rewards: \u20ac{lo:.0f} \u2013 \u20ac{hi:.0f}")

    # ------------------------------------------------------------------
    # Sector row creation / visibility
    # ------------------------------------------------------------------
    def _make_sector_row(self, parent, idx, row_offset):
        r = row_offset + idx
        widgets = []

        lbl_num = ttk.Label(parent, text=str(idx + 1), anchor=tk.CENTER)
        lbl_num.grid(row=r, column=0, padx=4, pady=2)
        widgets.append(lbl_num)

        sv_label = tk.StringVar()
        e_label = ttk.Entry(parent, textvariable=sv_label, width=14,
                             font=("Segoe UI", 10))
        e_label.grid(row=r, column=1, padx=4, pady=2)
        widgets.append(e_label)
        # Auto-fill value when user edits reward label and leaves the field
        e_label.bind("<FocusOut>",
                     lambda e, sv_l=sv_label, idx=idx: self._on_label_edit(
                         sv_l, idx))

        sv_value = tk.StringVar()
        e_value = ttk.Entry(parent, textvariable=sv_value, width=10,
                             font=("Segoe UI", 10))
        e_value.grid(row=r, column=2, padx=4, pady=2)
        widgets.append(e_value)

        sv_disabled = tk.BooleanVar(value=False)
        cb = ttk.Checkbutton(parent, variable=sv_disabled)
        cb.grid(row=r, column=3, padx=4, pady=2)
        widgets.append(cb)

        sv_prob = tk.StringVar(value="\u2014")
        lbl_prob = ttk.Label(parent, textvariable=sv_prob,
                              style="Result.TLabel", anchor=tk.CENTER)
        lbl_prob.grid(row=r, column=4, padx=4, pady=2, sticky=tk.EW)
        widgets.append(lbl_prob)

        sv_ev = tk.StringVar(value="\u2014")
        lbl_ev = ttk.Label(parent, textvariable=sv_ev,
                            style="Result.TLabel", anchor=tk.E)
        lbl_ev.grid(row=r, column=5, padx=4, pady=2, sticky=tk.EW)
        widgets.append(lbl_ev)

        sv_cum = tk.StringVar(value="\u2014")
        lbl_cum = ttk.Label(parent, textvariable=sv_cum,
                             style="Result.TLabel", anchor=tk.E)
        lbl_cum.grid(row=r, column=6, padx=4, pady=2, sticky=tk.EW)
        widgets.append(lbl_cum)

        return {
            "label": sv_label, "value": sv_value, "disabled": sv_disabled,
            "prob": sv_prob, "ev": sv_ev, "cum": sv_cum,
            "_widgets": widgets,
        }

    def _on_label_edit(self, sv_label, idx):
        """Auto-fill EUR value when user types a reward label."""
        label = sv_label.get().strip()
        if not label:
            return
        parsed = parse_reward_label(label)
        if parsed is not None:
            row = self._sector_rows[idx]
            if float(row["value"].get() or 0) != parsed:
                row["value"].set(
                    str(int(parsed)) if float(parsed).is_integer()
                    else f"{parsed:.2f}")

    def _show_rows(self, count):
        count = max(MIN_SECTORS, min(MAX_SECTORS, count))
        for i, row in enumerate(self._sector_rows):
            if i < count:
                for w in row["_widgets"]:
                    w.grid()
            else:
                for w in row["_widgets"]:
                    w.grid_remove()
                row["label"].set("")
                row["value"].set("")
                row["disabled"].set(False)
                row["prob"].set("\u2014")
                row["ev"].set("\u2014")
                row["cum"].set("\u2014")

    def _on_sector_count_change(self):
        try:
            n = self._num_sectors_var.get()
        except (tk.TclError, ValueError):
            return
        self._show_rows(max(MIN_SECTORS, min(MAX_SECTORS, n)))

    # ------------------------------------------------------------------
    # Populate / clear
    # ------------------------------------------------------------------
    def _fill_sectors(self, sectors):
        for i, row in enumerate(self._sector_rows):
            if i < len(sectors):
                s = sectors[i]
                row["label"].set(s["label"])
                row["value"].set(
                    f"{s['value']:.2f}" if not float(s["value"]).is_integer()
                    else str(int(s["value"])))
                row["disabled"].set(s["disabled"])
            else:
                row["label"].set("")
                row["value"].set("")
                row["disabled"].set(False)

    def _clear_results(self):
        for row in self._sector_rows:
            row["prob"].set("\u2014")
            row["ev"].set("\u2014")
            row["cum"].set("\u2014")
        self._summary_var.set("")
        self._detail_var.set("")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _generate(self):
        try:
            target = float(self._target_var.get())
            if target <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messagebox.showerror("Error", self._t("err_input"))
            return

        try:
            num = self._num_sectors_var.get()
        except (tk.TclError, ValueError):
            num = DEFAULT_NUM_SECTORS
        num = max(MIN_SECTORS, min(MAX_SECTORS, num))
        self._num_sectors_var.set(num)
        self._show_rows(num)

        try:
            spread = self._spread_var.get()
        except (tk.TclError, ValueError):
            spread = DEFAULT_SPREAD

        try:
            num_disabled = self._num_disabled_var.get()
        except (tk.TclError, ValueError):
            num_disabled = DEFAULT_DISABLED
        num_disabled = max(0, min(num - 1, num_disabled))

        try:
            dis_in_spread = self._dis_in_spread_var.get()
        except (tk.TclError, ValueError):
            dis_in_spread = True

        sectors = generate_sectors(target, num, spread=spread,
                                   num_disabled=num_disabled,
                                   disabled_in_spread=dis_in_spread)
        self._fill_sectors(sectors)
        self._update_spread_desc()
        self._recalculate()

    def _recalculate(self):
        self._clear_results()

        try:
            target = float(self._target_var.get())
            us_min = float(self._usmin_var.get())
            us_max = float(self._usmax_var.get())
        except (ValueError, TypeError):
            self._summary_var.set(self._t("err_invalid"))
            self._summary_lbl.configure(style="Red.TLabel")
            return

        # Validate undershoot range
        if us_min >= us_max:
            self._summary_var.set(self._t("err_undershoot"))
            self._summary_lbl.configure(style="Red.TLabel")
            return

        try:
            num = self._num_sectors_var.get()
        except (tk.TclError, ValueError):
            num = DEFAULT_NUM_SECTORS
        num = max(MIN_SECTORS, min(MAX_SECTORS, num))

        sectors = []
        for i in range(num):
            row = self._sector_rows[i]
            lbl = row["label"].get().strip()
            val_str = row["value"].get().strip()

            # Auto-fill value from label if value is empty/zero
            if lbl and not val_str:
                parsed = parse_reward_label(lbl)
                if parsed is not None:
                    val_str = (str(int(parsed)) if float(parsed).is_integer()
                               else f"{parsed:.2f}")
                    row["value"].set(val_str)

            if not lbl and not val_str:
                continue
            try:
                val = float(val_str)
            except (ValueError, TypeError):
                self._summary_var.set(
                    self._t("err_bad_value").format(i + 1, val_str))
                self._summary_lbl.configure(style="Red.TLabel")
                return
            sectors.append({
                "label": lbl or "?",
                "value": val,
                "disabled": row["disabled"].get(),
            })

        if len(sectors) < 2:
            self._summary_var.set(self._t("err_min_sectors"))
            self._summary_lbl.configure(style="Red.TLabel")
            return

        cfg = {
            "name": f"Wheel \u20ac{target:.0f}",
            "target": target,
            "undershoot_min_pct": us_min,
            "undershoot_max_pct": us_max,
            "sectors": sectors,
        }

        result_sectors, ev, status, msg = solve_wheel_precise(cfg)

        if status != "ok":
            self._summary_var.set(self._t("err_no_solution"))
            self._summary_lbl.configure(style="Red.TLabel")
            self._detail_var.set(msg)
            self._last_result = None
            return

        solver_warning = msg

        cum = 0.0
        ri = 0
        for i in range(num):
            row = self._sector_rows[i]
            if not row["label"].get().strip() and not row["value"].get().strip():
                continue
            if ri >= len(result_sectors):
                break
            s = result_sectors[ri]
            ev_c = s["probability"] * s["value"] / 100.0
            cum += ev_c
            p = s["probability"]
            if float(p).is_integer():
                row["prob"].set(f"{int(p)}%")
            else:
                row["prob"].set(f"{p:.2f}%")
            row["ev"].set(f"\u20ac{ev_c:.2f}")
            row["cum"].set(f"\u20ac{cum:.2f}")
            ri += 1

        undershoot = (1 - ev / target) * 100
        self._summary_var.set(
            f"Total EV: \u20ac{ev:.2f}   |   "
            f"Undershoot: {undershoot:.2f}% of \u20ac{target:.2f}")
        if solver_warning:
            self._summary_lbl.configure(style="Red.TLabel")
        else:
            self._summary_lbl.configure(style="Green.TLabel")
        detail = (
            f"Acceptable range: \u20ac{target * (1 - us_max/100):.2f} \u2013 "
            f"\u20ac{target * (1 - us_min/100):.2f}   |   "
            f"Probabilities sum to "
            f"{sum(s['probability'] for s in result_sectors):.2f}%")
        if solver_warning:
            detail += f"   |   {solver_warning}"
        self._detail_var.set(detail)
        self._last_result = (cfg["name"], result_sectors)

    def _export_csv(self):
        if self._last_result is None:
            messagebox.showinfo(self._t("export_title"),
                                self._t("export_none"))
            return
        path = filedialog.asksaveasfilename(
            title=self._t("export_title"),
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("All files", "*.*")],
            initialfile="wheel_output.csv")
        if not path:
            return
        name, sectors = self._last_result
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Wheel", "Sector", "Reward", "EUR Value",
                            "Probability %", "EV Contribution", "Disabled"])
                for i, s in enumerate(sectors, 1):
                    ev_c = s["probability"] * s["value"] / 100.0
                    prob = s["probability"]
                    prob_str = (f"{prob:.2f}" if not float(prob).is_integer()
                                else str(int(prob)))
                    w.writerow([name, i, s["label"], f"{s['value']:.2f}",
                                prob_str, f"{ev_c:.4f}",
                                "Yes" if s["disabled"] else "No"])
            messagebox.showinfo(self._t("export_title"),
                                self._t("export_done").format(path))
        except Exception as exc:
            messagebox.showerror("Export Error", str(exc))


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app = WheelSolverApp()
    app.mainloop()
