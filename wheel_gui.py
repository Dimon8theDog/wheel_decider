#!/usr/bin/env python3
"""Wheel Solver GUI - Interactive bonus wheel configuration tool.

Type a bonus cost, adjust the reward spread, click Generate, get a complete
wheel with rewards and probabilities.

Usage:
    python wheel_gui.py
"""

import math
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
# Spread → ratio mapping
# ---------------------------------------------------------------------------
def _spread_to_ratios(spread):
    """Convert a spread value (1–10) to generation parameters.

    Returns (min_ratio, max_ratio).

    spread=1  (tight):  rewards ≈ 0.70x – 1.30x target
    spread=5  (default): rewards ≈ 0.20x – 3.0x target
    spread=10 (wide):   rewards ≈ 0.05x – 6.0x target
    """
    t = max(0.0, min(1.0, (spread - 1) / 9))  # normalise to 0..1
    # Log-interpolate between tight and wide endpoints
    min_r = 0.70 * (0.05 / 0.70) ** t     # 0.70 → 0.05
    max_r = 1.30 * (6.00 / 1.30) ** t     # 1.30 → 6.00
    return min_r, max_r


# ---------------------------------------------------------------------------
# Auto-generation of sector rewards
# ---------------------------------------------------------------------------
def _compute_ratios(num_sectors, min_ratio=0.20, max_ratio=3.0):
    """Value-multiplier ratios for *num_sectors* sectors.

    All sectors are log-spaced from *min_ratio* to *max_ratio*.
    """
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


def _snap_to_fs(raw_eur, min_above, max_value=None):
    """Nearest nice FS count → (eur_value, label) or (None, None)."""
    target_fs = raw_eur / FS_RATE
    candidates = [
        (fs, abs(fs - target_fs))
        for fs in NICE_FS
        if fs * FS_RATE > min_above
        and (max_value is None or fs * FS_RATE <= max_value)
    ]
    if not candidates:
        return None, None
    best_fs = min(candidates, key=lambda x: x[1])[0]
    return best_fs * FS_RATE, f"{best_fs} FS"


def _snap_to_hb_fs(raw_eur, min_above, max_value=None):
    """Nearest nice high-bet FS count → (eur_value, label) or (None, None)."""
    target_fs = raw_eur / HB_FS_RATE
    candidates = [
        (fs, abs(fs - target_fs))
        for fs in NICE_HB_FS
        if fs * HB_FS_RATE > min_above
        and (max_value is None or fs * HB_FS_RATE <= max_value)
    ]
    if not candidates:
        return None, None
    best_fs = min(candidates, key=lambda x: x[1])[0]
    return best_fs * HB_FS_RATE, f"{best_fs} HB FS"


def _snap_to_eur(raw_eur, min_above, max_value=None):
    """Snap to a clean round EUR amount above *min_above* (≤ *max_value*)."""
    if raw_eur <= 50:
        step = 5
    elif raw_eur <= 200:
        step = 10
    elif raw_eur <= 500:
        step = 25
    else:
        step = 50

    eur = max(round(raw_eur / step) * step, step)
    if eur <= min_above:
        eur = (int(min_above / step) + 1) * step

    if max_value is not None and eur > max_value:
        eur = int(max_value / step) * step
        if eur <= min_above:
            eur = int(max_value)
            if eur <= min_above:
                return None, None

    return float(eur), f"\u20ac{int(eur)}"


def _snap_candidates(raw_eur):
    """All snap options across reward types, sorted by closeness to raw_eur."""
    candidates = []

    # Regular FS options
    for fs in NICE_FS:
        val = fs * FS_RATE
        candidates.append((abs(val - raw_eur), val, f"{fs} FS"))

    # HB FS options
    for fs in NICE_HB_FS:
        val = fs * HB_FS_RATE
        candidates.append((abs(val - raw_eur), val, f"{fs} HB FS"))

    # EUR — generate several nearby round amounts so there are alternatives
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


def generate_sectors(target, num_sectors=DEFAULT_NUM_SECTORS,
                     spread=DEFAULT_SPREAD, num_disabled=DEFAULT_DISABLED,
                     disabled_in_spread=True):
    """Auto-generate sector rewards for a given bonus cost and spread.

    Args:
        target:            Bonus cost in EUR.
        num_sectors:       Total sectors.
        spread:            1–10 controlling how far rewards deviate from the target.
                           1 = tight (rewards ≈ target), 10 = very wide range.
        num_disabled:      How many sectors to mark as disabled (highest-value ones).
        disabled_in_spread: If True, disabled sectors stay within the spread range.
                           If False, disabled sectors are aspirational prizes
                           placed beyond the spread ceiling.
    """
    min_ratio, max_ratio = _spread_to_ratios(spread)
    num_disabled = max(0, min(num_disabled, num_sectors - 1))
    num_active = num_sectors - num_disabled

    # Active sectors ALWAYS span the full spread range
    active_ratios = _compute_ratios(num_active, min_ratio, max_ratio)

    # Disabled sectors placed either within or beyond the spread
    if num_disabled == 0:
        dis_ratios = []
    elif disabled_in_spread:
        dis_lo = active_ratios[-1] * 1.15 if active_ratios else max_ratio * 0.8
        dis_ratios = _compute_ratios(num_disabled, dis_lo, max_ratio) \
            if num_disabled > 1 else [max(dis_lo, max_ratio * 0.9)]
    else:
        dis_base = max_ratio * 1.4
        dis_ratios = [dis_base * (1.3 ** d) for d in range(num_disabled)]

    # Snap each sector to closest unused nice value
    used_labels = set()
    sectors = []

    for ratio in active_ratios:
        candidates = _snap_candidates(target * ratio)
        for _, val, label in candidates:
            if label not in used_labels:
                used_labels.add(label)
                sectors.append({"label": label, "value": val, "disabled": False})
                break

    for ratio in dis_ratios:
        candidates = _snap_candidates(target * ratio)
        for _, val, label in candidates:
            if label not in used_labels:
                used_labels.add(label)
                sectors.append({"label": label, "value": val, "disabled": True})
                break

    # Sort by value for clean display
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
        self.title("Wheel Solver")
        self.configure(bg=BG)
        self.geometry("900x740")
        self.minsize(800, 560)

        self._setup_styles()
        self._build_ui()

        # Initial state
        self._target_var.set("65")
        self._generate()

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
        s.configure("TSpinbox", fieldbackground=BG_INPUT, foreground=FG,
                     padding=3)

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        pad = dict(padx=18, pady=4)

        # ── Title ──
        ttk.Label(self, text="Wheel Solver", style="Title.TLabel").pack(
            anchor=tk.W, padx=18, pady=(14, 2))
        ttk.Label(
            self,
            text="Enter a bonus cost, adjust the spread, click Generate.",
            style="Dim.TLabel",
        ).pack(anchor=tk.W, padx=18, pady=(0, 8))

        # ── Input row 1 ──
        inp = ttk.Frame(self)
        inp.pack(fill=tk.X, **pad)

        ttk.Label(inp, text="Bonus cost (\u20ac):").pack(side=tk.LEFT)
        self._target_var = tk.StringVar()
        te = ttk.Entry(inp, textvariable=self._target_var, width=8,
                        font=("Segoe UI", 12))
        te.pack(side=tk.LEFT, padx=(6, 16))
        te.bind("<Return>", lambda e: self._generate())

        ttk.Label(inp, text="Sectors:").pack(side=tk.LEFT)
        self._num_sectors_var = tk.IntVar(value=DEFAULT_NUM_SECTORS)
        sb = ttk.Spinbox(inp, from_=MIN_SECTORS, to=MAX_SECTORS,
                          textvariable=self._num_sectors_var, width=4,
                          font=("Segoe UI", 10),
                          command=self._on_sector_count_change)
        sb.pack(side=tk.LEFT, padx=(4, 16))
        sb.bind("<Return>", lambda e: self._on_sector_count_change())

        ttk.Label(inp, text="Disabled:").pack(side=tk.LEFT)
        self._num_disabled_var = tk.IntVar(value=DEFAULT_DISABLED)
        sb_dis = ttk.Spinbox(inp, from_=0, to=MAX_SECTORS - 1,
                              textvariable=self._num_disabled_var, width=4,
                              font=("Segoe UI", 10))
        sb_dis.pack(side=tk.LEFT, padx=(4, 4))

        self._dis_in_spread_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(inp, text="In spread",
                        variable=self._dis_in_spread_var).pack(
            side=tk.LEFT, padx=(0, 16))

        ttk.Label(inp, text="Undershoot:").pack(side=tk.LEFT)
        self._usmin_var = tk.StringVar(value="5")
        ttk.Entry(inp, textvariable=self._usmin_var, width=4).pack(
            side=tk.LEFT, padx=(4, 0))
        ttk.Label(inp, text="% \u2013").pack(side=tk.LEFT, padx=2)
        self._usmax_var = tk.StringVar(value="8")
        ttk.Entry(inp, textvariable=self._usmax_var, width=4).pack(
            side=tk.LEFT, padx=(0, 4))
        ttk.Label(inp, text="%").pack(side=tk.LEFT)

        # ── Input row 2 — Reward spread slider ──
        slider_frame = ttk.Frame(self)
        slider_frame.pack(fill=tk.X, padx=18, pady=(2, 6))

        ttk.Label(slider_frame, text="Reward spread:").pack(side=tk.LEFT)
        ttk.Label(slider_frame, text="Tight", style="Dim.TLabel").pack(
            side=tk.LEFT, padx=(8, 0))

        self._spread_var = tk.IntVar(value=DEFAULT_SPREAD)
        self._spread_scale = tk.Scale(
            slider_frame,
            from_=1, to=10,
            orient=tk.HORIZONTAL,
            variable=self._spread_var,
            bg=BG, fg=FG,
            troughcolor=BG_INPUT,
            highlightthickness=0,
            sliderrelief=tk.FLAT,
            activebackground=ACCENT_HI,
            font=("Segoe UI", 9),
            showvalue=True,
            length=280,
        )
        self._spread_scale.pack(side=tk.LEFT, padx=4)

        ttk.Label(slider_frame, text="Wide", style="Dim.TLabel").pack(
            side=tk.LEFT, padx=(0, 12))

        self._spread_desc_var = tk.StringVar()
        ttk.Label(slider_frame, textvariable=self._spread_desc_var,
                  style="Dim.TLabel").pack(side=tk.LEFT)
        self._update_spread_desc()
        self._spread_var.trace_add("write", lambda *_: self._update_spread_desc())

        # ── Buttons ──
        btn = ttk.Frame(self)
        btn.pack(fill=tk.X, **pad)
        ttk.Button(btn, text="Generate Wheel", style="Accent.TButton",
                   command=self._generate).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn, text="Recalculate Probs",
                   command=self._recalculate).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn, text="Export CSV",
                   command=self._export_csv).pack(side=tk.LEFT)

        # ── Sector table ──
        tbl_outer = ttk.Frame(self)
        tbl_outer.pack(fill=tk.BOTH, expand=True, padx=18, pady=(8, 0))

        self._tbl = ttk.Frame(tbl_outer)
        self._tbl.pack(fill=tk.BOTH, expand=True)

        self._headers = [
            ("#", 3), ("Reward", 14), ("EUR Value", 10), ("Dis.", 4),
            ("Prob %", 7), ("EV Contrib", 10), ("Cum. EV", 10),
        ]
        for j, (text, _w) in enumerate(self._headers):
            ttk.Label(self._tbl, text=text, style="Dim.TLabel",
                      anchor=tk.CENTER).grid(
                row=0, column=j, padx=4, pady=(0, 2), sticky=tk.EW)

        ttk.Separator(self._tbl, orient=tk.HORIZONTAL).grid(
            row=1, column=0, columnspan=len(self._headers),
            sticky=tk.EW, pady=2)

        for j in range(len(self._headers)):
            self._tbl.columnconfigure(j, weight=1)

        self._sector_rows = []
        for i in range(MAX_SECTORS):
            self._sector_rows.append(
                self._make_sector_row(self._tbl, i, row_offset=2))
        self._show_rows(DEFAULT_NUM_SECTORS)

        # ── Summary ──
        self._summary_var = tk.StringVar()
        self._summary_lbl = ttk.Label(self, textvariable=self._summary_var,
                                       style="Green.TLabel")
        self._summary_lbl.pack(anchor=tk.W, padx=22, pady=(8, 0))

        self._detail_var = tk.StringVar()
        ttk.Label(self, textvariable=self._detail_var,
                  style="Dim.TLabel").pack(anchor=tk.W, padx=22, pady=(2, 12))

        self._last_result = None

    # ------------------------------------------------------------------
    # Spread description
    # ------------------------------------------------------------------
    def _update_spread_desc(self):
        """Update the label next to the slider showing the reward range."""
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
            f"Active rewards: \u20ac{lo:.0f} \u2013 \u20ac{hi:.0f}"
        )

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
                    else str(int(s["value"]))
                )
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
            messagebox.showerror("Input Error",
                                 "Bonus cost must be a positive number.")
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
            self._summary_var.set("Invalid input values.")
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
            if not lbl and not val_str:
                continue
            try:
                val = float(val_str)
            except (ValueError, TypeError):
                self._summary_var.set(
                    f"Bad value in sector {i+1}: '{val_str}'")
                self._summary_lbl.configure(style="Red.TLabel")
                return
            sectors.append({
                "label": lbl or "?",
                "value": val,
                "disabled": row["disabled"].get(),
            })

        if len(sectors) < 2:
            self._summary_var.set("Need at least 2 sectors.")
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
            self._summary_var.set("No solution found")
            self._summary_lbl.configure(style="Red.TLabel")
            self._detail_var.set(msg)
            self._last_result = None
            return

        solver_warning = msg  # may be non-empty if rounding drifted

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
            # Show clean format: integer if whole, 2 decimals otherwise
            if p == int(p):
                row["prob"].set(f"{int(p)}%")
            else:
                row["prob"].set(f"{p:.2f}%")
            row["ev"].set(f"\u20ac{ev_c:.2f}")
            row["cum"].set(f"\u20ac{cum:.2f}")
            ri += 1

        undershoot = (1 - ev / target) * 100
        self._summary_var.set(
            f"Total EV: \u20ac{ev:.2f}   |   "
            f"Undershoot: {undershoot:.2f}% of \u20ac{target:.2f}"
        )
        if solver_warning:
            self._summary_lbl.configure(style="Red.TLabel")
        else:
            self._summary_lbl.configure(style="Green.TLabel")
        detail = (
            f"Acceptable range: \u20ac{target * (1 - us_max/100):.2f} \u2013 "
            f"\u20ac{target * (1 - us_min/100):.2f}   |   "
            f"Probabilities sum to "
            f"{sum(s['probability'] for s in result_sectors):.2f}%"
        )
        if solver_warning:
            detail += f"   |   {solver_warning}"
        self._detail_var.set(detail)
        self._last_result = (cfg["name"], result_sectors)

    def _export_csv(self):
        if self._last_result is None:
            messagebox.showinfo("Export",
                                "No results yet. Generate a wheel first.")
            return
        path = filedialog.asksaveasfilename(
            title="Export CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("All files", "*.*")],
            initialfile="wheel_output.csv",
        )
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
                    prob_str = f"{prob:.2f}" if prob != int(prob) else str(int(prob))
                    w.writerow([name, i, s["label"], f"{s['value']:.2f}",
                                prob_str, f"{ev_c:.4f}",
                                "Yes" if s["disabled"] else "No"])
            messagebox.showinfo("Exported", f"Saved to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export Error", str(exc))


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app = WheelSolverApp()
    app.mainloop()
