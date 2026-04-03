#!/usr/bin/env python3
"""Wheel Solver - Calculates optimal bonus wheel configurations for iGaming CRM.

Solves for integer-percentage probability distributions across wheel sectors
such that the expected value undershoots a target flat bonus by a configured margin.

Usage:
    python wheel_solver.py                      # Uses built-in default config
    python wheel_solver.py --config wheels.json  # Uses custom JSON/YAML config
"""

import argparse
import csv
import json
import math
import sys
from pathlib import Path

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


# ---------------------------------------------------------------------------
# Default configuration (5 wheels)
# ---------------------------------------------------------------------------
DEFAULT_CONFIG = {
    "wheels": [
        {
            "name": "Wheel 1 - \u20ac5",
            "target": 5,
            "undershoot_min_pct": 5,
            "undershoot_max_pct": 8,
            "sectors": [
                {"label": "5 FS", "value": 1, "disabled": False},
                {"label": "15 FS", "value": 3, "disabled": False},
                {"label": "25 FS", "value": 5, "disabled": False},
                {"label": "\u20ac10", "value": 10, "disabled": False},
                {"label": "\u20ac15", "value": 15, "disabled": False},
                {"label": "\u20ac25", "value": 25, "disabled": True},
            ],
        },
        {
            "name": "Wheel 2 - \u20ac10",
            "target": 10,
            "undershoot_min_pct": 5,
            "undershoot_max_pct": 8,
            "sectors": [
                {"label": "10 FS", "value": 2, "disabled": False},
                {"label": "25 FS", "value": 5, "disabled": False},
                {"label": "50 FS", "value": 10, "disabled": False},
                {"label": "\u20ac20", "value": 20, "disabled": False},
                {"label": "\u20ac30", "value": 30, "disabled": False},
                {"label": "\u20ac50", "value": 50, "disabled": True},
            ],
        },
        {
            "name": "Wheel 3 - \u20ac20",
            "target": 20,
            "undershoot_min_pct": 5,
            "undershoot_max_pct": 8,
            "sectors": [
                {"label": "25 FS", "value": 5, "disabled": False},
                {"label": "50 FS", "value": 10, "disabled": False},
                {"label": "100 FS", "value": 20, "disabled": False},
                {"label": "\u20ac35", "value": 35, "disabled": False},
                {"label": "\u20ac60", "value": 60, "disabled": False},
                {"label": "\u20ac150", "value": 150, "disabled": True},
            ],
        },
        {
            "name": "Wheel 4 - \u20ac35",
            "target": 35,
            "undershoot_min_pct": 5,
            "undershoot_max_pct": 8,
            "sectors": [
                {"label": "50 FS", "value": 10, "disabled": False},
                {"label": "100 FS", "value": 20, "disabled": False},
                {"label": "175 FS", "value": 35, "disabled": False},
                {"label": "\u20ac60", "value": 60, "disabled": False},
                {"label": "\u20ac100", "value": 100, "disabled": False},
                {"label": "\u20ac200", "value": 200, "disabled": True},
            ],
        },
        {
            "name": "Wheel 5 - \u20ac65",
            "target": 65,
            "undershoot_min_pct": 5,
            "undershoot_max_pct": 8,
            "sectors": [
                {"label": "100 FS", "value": 20, "disabled": False},
                {"label": "200 FS", "value": 40, "disabled": False},
                {"label": "\u20ac50", "value": 50, "disabled": False},
                {"label": "\u20ac100", "value": 100, "disabled": False},
                {"label": "\u20ac150", "value": 150, "disabled": False},
                {"label": "\u20ac300", "value": 300, "disabled": True},
            ],
        },
    ]
}


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------
def load_config(path=None):
    """Load wheel configuration from a JSON/YAML file, or return the default."""
    if path is None:
        return DEFAULT_CONFIG
    p = Path(path)
    if not p.exists():
        print(f"Error: Config file '{path}' not found.", file=sys.stderr)
        sys.exit(1)
    text = p.read_text(encoding="utf-8")
    if p.suffix in (".yaml", ".yml"):
        if not _HAS_YAML:
            print(
                "Error: PyYAML is required for YAML config files.\n"
                "Install with: pip install pyyaml\n"
                "Or use a JSON config file instead.",
                file=sys.stderr,
            )
            sys.exit(1)
        return yaml.safe_load(text)
    return json.loads(text)


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------
def solve_wheel(wheel_cfg):
    """Find optimal integer-percentage probabilities for a wheel's sectors.

    Returns:
        (result_sectors, total_ev, status, message)
        - result_sectors: list of dicts {label, value, disabled, probability}
          in original config order (None when status != 'ok')
        - total_ev: achieved expected value in EUR
        - status: 'ok' | 'no_solution'
        - message: diagnostic string (empty on success)
    """
    sectors = wheel_cfg["sectors"]
    target = float(wheel_cfg["target"])
    us_min = float(wheel_cfg["undershoot_min_pct"])
    us_max = float(wheel_cfg["undershoot_max_pct"])

    # Acceptable EV window
    ev_low = target * (1 - us_max / 100)
    ev_high = target * (1 - us_min / 100)

    # ---- Partition sectors ------------------------------------------------
    active_idx = []          # indices into *sectors* list, to be solved
    fixed = {}               # sector-index -> locked probability (int %)

    for i, s in enumerate(sectors):
        if s.get("disabled", False):
            fixed[i] = 0
        elif "locked_probability" in s:
            fixed[i] = int(s["locked_probability"])
        else:
            active_idx.append(i)

    # Sort active sectors by EUR value ascending (cheapest first)
    active_idx.sort(key=lambda i: sectors[i]["value"])
    vals = [float(sectors[i]["value"]) for i in active_idx]
    n = len(active_idx)

    fixed_prob = sum(fixed.values())
    fixed_ev = sum(fixed[i] * sectors[i]["value"] / 100.0 for i in fixed)
    budget = 100 - fixed_prob

    # ---- Trivial edge cases -----------------------------------------------
    if budget < 0:
        return None, 0.0, "no_solution", "Locked probabilities exceed 100%."

    if n == 0:
        if ev_low <= fixed_ev <= ev_high:
            res = [
                {
                    "label": s["label"],
                    "value": s["value"],
                    "disabled": s.get("disabled", False),
                    "probability": fixed.get(i, 0),
                }
                for i, s in enumerate(sectors)
            ]
            return res, fixed_ev, "ok", ""
        return None, 0.0, "no_solution", (
            f"All sectors locked/disabled. EV=\u20ac{fixed_ev:.2f} is outside the "
            f"required range [\u20ac{ev_low:.2f}, \u20ac{ev_high:.2f}]."
        )

    # ---- Weighted-sum targets ---------------------------------------------
    # ws = sum(p_i * val_i)  -->  EV = ws / 100 + fixed_ev
    ws_lo = (ev_low - fixed_ev) * 100
    ws_hi = (ev_high - fixed_ev) * 100
    mid_ws = (ws_lo + ws_hi) / 2

    min_p = 1  # absolute minimum probability per active sector

    # ---- Feasibility check ------------------------------------------------
    if budget < n * min_p:
        return None, 0.0, "no_solution", (
            f"Probability budget ({budget}%) is too small for {n} active sectors "
            f"(need at least {n * min_p}% total)."
        )

    flex_total = budget - n * min_p
    base_ws_total = sum(min_p * v for v in vals)
    ws_min_possible = base_ws_total + flex_total * vals[0]
    ws_max_possible = base_ws_total + flex_total * vals[-1]

    if ws_max_possible < ws_lo:
        max_ev = ws_max_possible / 100 + fixed_ev
        return None, 0.0, "no_solution", (
            f"Sector values are too low to reach the target EV range. "
            f"Maximum achievable EV = \u20ac{max_ev:.2f}, but minimum required = "
            f"\u20ac{ev_low:.2f}. Suggestion: increase sector reward values or "
            f"lower the target."
        )

    if ws_min_possible > ws_hi:
        min_ev = ws_min_possible / 100 + fixed_ev
        return None, 0.0, "no_solution", (
            f"Sector values are too high — even the minimum EV exceeds the target "
            f"range. Minimum achievable EV = \u20ac{min_ev:.2f}, but maximum "
            f"allowed = \u20ac{ev_high:.2f}. Suggestion: decrease sector reward "
            f"values or raise the target."
        )

    # ---- Precompute suffix base sums for pruning --------------------------
    sfx = [0.0] * (n + 1)
    for i in range(n - 1, -1, -1):
        sfx[i] = sfx[i + 1] + min_p * vals[i]

    # ---- Scoring function -------------------------------------------------
    def score(probs, ws):
        """Higher is better.  Tuple compared lexicographically."""
        # Priority 1 – descending probability order
        desc = all(probs[j] >= probs[j + 1] for j in range(n - 1))
        # Priority 2 – every sector >= 3%
        meets_3 = min(probs) >= 3
        # Priority 3 – most probabilities divisible by 5
        rnd = sum(1 for p in probs if p % 5 == 0)
        # Priority 4 – closest to midpoint of undershoot range
        close = -abs(ws - mid_ws)
        return (desc, meets_3, rnd, close)

    # ---- Brute-force search with branch pruning ---------------------------
    best_probs = None
    best_score = None

    def search(idx, rem, lo, hi, cur, cur_ws):
        nonlocal best_probs, best_score
        slots = n - idx

        # Base case: single remaining sector
        if idx == n - 1:
            p = rem
            if p < min_p:
                return
            w = p * vals[idx]
            if lo <= w <= hi:
                probs = tuple(cur) + (p,)
                ws = cur_ws + w
                s = score(probs, ws)
                if best_score is None or s > best_score:
                    best_probs, best_score = probs, s
            return

        # Optimised base case: two remaining sectors (exact inner bounds)
        if idx == n - 2:
            va, vb = vals[idx], vals[idx + 1]
            d = va - vb  # typically < 0 (vals sorted ascending)
            base = rem * vb
            if d == 0:
                # Weighted sum is fixed regardless of how we split
                if lo <= base <= hi:
                    for p in range(min_p, rem - min_p + 1):
                        probs = tuple(cur) + (p, rem - p)
                        s = score(probs, cur_ws + base)
                        if best_score is None or s > best_score:
                            best_probs, best_score = probs, s
                return
            # Compute exact valid range for p (sector idx probability)
            if d < 0:
                p_lo_ev = math.ceil((hi - base) / d - 1e-9)
                p_hi_ev = math.floor((lo - base) / d + 1e-9)
            else:
                p_lo_ev = math.ceil((lo - base) / d - 1e-9)
                p_hi_ev = math.floor((hi - base) / d + 1e-9)
            p_lo = max(min_p, p_lo_ev)
            p_hi = min(rem - min_p, p_hi_ev)
            for p in range(p_lo, p_hi + 1):
                q = rem - p
                w = p * va + q * vb
                # Safety re-check (guards against float rounding in bounds)
                if lo <= w <= hi:
                    probs = tuple(cur) + (p, q)
                    s = score(probs, cur_ws + w)
                    if best_score is None or s > best_score:
                        best_probs, best_score = probs, s
            return

        # General case: iterate p for sector *idx*, prune with suffix bounds
        max_p = rem - (slots - 1) * min_p
        for p in range(min_p, max_p + 1):
            nr = rem - p
            nlo = lo - p * vals[idx]
            nhi = hi - p * vals[idx]
            fl = nr - (slots - 1) * min_p
            if fl < 0:
                continue
            # Achievable weighted-sum range for sectors (idx+1 .. n-1)
            mn = sfx[idx + 1] + fl * vals[idx + 1]
            mx = sfx[idx + 1] + fl * vals[n - 1]
            if mx < nlo or mn > nhi:
                continue
            cur.append(p)
            search(idx + 1, nr, nlo, nhi, cur, cur_ws + p * vals[idx])
            cur.pop()

    search(0, budget, ws_lo, ws_hi, [], 0.0)

    if best_probs is None:
        return None, 0.0, "no_solution", (
            f"No integer-percentage solution found within the EV range "
            f"[\u20ac{ev_low:.2f}, \u20ac{ev_high:.2f}] with minimum {min_p}% per "
            f"sector. Suggestion: widen the undershoot range or adjust sector values."
        )

    # ---- Map solved probabilities back to original sector order -----------
    pmap = {active_idx[j]: best_probs[j] for j in range(n)}
    total_ev = fixed_ev + sum(best_probs[j] * vals[j] for j in range(n)) / 100.0

    result = []
    for i, s in enumerate(sectors):
        result.append(
            {
                "label": s["label"],
                "value": s["value"],
                "disabled": s.get("disabled", False),
                "probability": fixed.get(i, pmap.get(i, 0)),
            }
        )
    return result, total_ev, "ok", ""


# ---------------------------------------------------------------------------
# Precise solver (decimal probabilities via parametric power-law)
# ---------------------------------------------------------------------------
def _largest_remainder_round(raw_pcts, total, step):
    """Round *raw_pcts* so they sum to *total* using largest-remainder method.

    Each value is rounded to the nearest multiple of *step* (e.g. 0.01).
    Returns a list of floats.
    """
    slots = round(total / step)          # how many quanta we must distribute
    floored = [math.floor(p / step) for p in raw_pcts]
    remainders = [p / step - f for p, f in zip(raw_pcts, floored)]
    diff = slots - sum(floored)

    # Give one extra quantum to the entries with the largest remainders
    indices = sorted(range(len(remainders)), key=lambda i: -remainders[i])
    for i in range(int(round(diff))):
        floored[indices[i]] += 1

    return [f * step for f in floored]


def solve_wheel_precise(wheel_cfg, precision=0.01, min_prob=1.0):
    """Find optimal decimal-percentage probabilities using a power-law model.

    Instead of brute-forcing integer percentages, this solver uses a
    parametric approach:

      weight[i] = (n - i) ** k          (sectors sorted by value ascending)
      probability[i] = weight[i] / sum(weights) * budget

    A binary search on exponent *k* finds the value that puts the EV at the
    midpoint of the acceptable undershoot window.  Probabilities are then
    rounded to the nearest *precision* (default 0.01%) using the
    largest-remainder method so they still sum to exactly 100%.

    Args:
        wheel_cfg:  dict with keys: target, undershoot_min_pct,
                    undershoot_max_pct, sectors (list of dicts with
                    label, value, disabled).
        precision:  probability granularity in %-points (0.01 = hundredths).
        min_prob:   minimum probability for any active sector (default 1%).

    Returns:
        (result_sectors, total_ev, status, message)  — same shape as solve_wheel().
    """
    sectors = wheel_cfg["sectors"]
    target = float(wheel_cfg["target"])
    us_min = float(wheel_cfg["undershoot_min_pct"])
    us_max = float(wheel_cfg["undershoot_max_pct"])

    ev_low = target * (1 - us_max / 100)
    ev_high = target * (1 - us_min / 100)
    ev_mid = (ev_low + ev_high) / 2

    # ---- Partition sectors ------------------------------------------------
    active_idx = []
    fixed = {}

    for i, s in enumerate(sectors):
        if s.get("disabled", False):
            fixed[i] = 0.0
        elif "locked_probability" in s:
            fixed[i] = float(s["locked_probability"])
        else:
            active_idx.append(i)

    # Sort active sectors by EUR value ascending
    active_idx.sort(key=lambda i: sectors[i]["value"])
    vals = [float(sectors[i]["value"]) for i in active_idx]
    n = len(active_idx)

    fixed_prob = sum(fixed.values())
    fixed_ev = sum(fixed[i] * sectors[i]["value"] / 100.0 for i in fixed)
    budget = 100.0 - fixed_prob

    # ---- Trivial edge cases -----------------------------------------------
    if budget < 0:
        return None, 0.0, "no_solution", "Locked probabilities exceed 100%."

    if n == 0:
        if ev_low <= fixed_ev <= ev_high:
            res = [
                {
                    "label": s["label"],
                    "value": s["value"],
                    "disabled": s.get("disabled", False),
                    "probability": fixed.get(i, 0.0),
                }
                for i, s in enumerate(sectors)
            ]
            return res, fixed_ev, "ok", ""
        return None, 0.0, "no_solution", (
            "All sectors locked/disabled. EV=€%.2f outside range [€%.2f, €%.2f]."
            % (fixed_ev, ev_low, ev_high)
        )

    if n == 1:
        # Only one active sector — probability = budget, check EV
        p = budget
        ev = fixed_ev + p * vals[0] / 100.0
        if ev_low <= ev <= ev_high:
            pmap = {active_idx[0]: round(p / precision) * precision}
            result = []
            for i, s in enumerate(sectors):
                result.append({
                    "label": s["label"],
                    "value": s["value"],
                    "disabled": s.get("disabled", False),
                    "probability": fixed.get(i, pmap.get(i, 0.0)),
                })
            return result, ev, "ok", ""
        return None, 0.0, "no_solution", (
            "Single active sector cannot hit the target EV range."
        )

    # ---- Feasibility check ------------------------------------------------
    min_budget_needed = n * min_prob
    if budget < min_budget_needed:
        return None, 0.0, "no_solution", (
            "Probability budget (%.1f%%) too small for %d active sectors "
            "(need at least %.1f%%)." % (budget, n, min_budget_needed)
        )

    # Check if EV range is achievable at all
    # Min EV: all budget on cheapest sector
    # Max EV: all budget on most expensive sector
    flex = budget - n * min_prob
    base_ws = sum(min_prob * v for v in vals)
    ws_min = base_ws + flex * vals[0]
    ws_max = base_ws + flex * vals[-1]
    ev_min_possible = fixed_ev + ws_min / 100.0
    ev_max_possible = fixed_ev + ws_max / 100.0

    if ev_max_possible < ev_low:
        return None, 0.0, "no_solution", (
            "Sector values too low. Max achievable EV = €%.2f, "
            "but minimum required = €%.2f." % (ev_max_possible, ev_low)
        )
    if ev_min_possible > ev_high:
        return None, 0.0, "no_solution", (
            "Sector values too high. Min achievable EV = €%.2f, "
            "but maximum allowed = €%.2f." % (ev_min_possible, ev_high)
        )

    # ---- Power-law weight function ----------------------------------------
    def compute_probs_and_ev(k):
        """For exponent k, compute raw probabilities and EV."""
        # weight[i] = (n - i) ** k   (i=0 is cheapest → highest weight)
        weights = [(n - i) ** k for i in range(n)]
        w_sum = sum(weights)
        raw_probs = [w / w_sum * budget for w in weights]

        # Enforce minimum probability
        clamped = [max(p, min_prob) for p in raw_probs]
        excess = sum(clamped) - budget
        if excess > 0:
            # Redistribute excess from largest probabilities
            for _ in range(100):  # safety
                overshoot = sum(clamped) - budget
                if abs(overshoot) < 1e-12:
                    break
                # Reduce proportionally from sectors above minimum
                above = [(i, clamped[i] - min_prob) for i in range(n)
                         if clamped[i] > min_prob]
                total_above = sum(a for _, a in above)
                if total_above <= 0:
                    break
                for i, a in above:
                    clamped[i] -= overshoot * (a / total_above)
                    clamped[i] = max(clamped[i], min_prob)

        ev = fixed_ev + sum(clamped[j] * vals[j] for j in range(n)) / 100.0
        return clamped, ev

    # ---- Binary search on exponent k to hit target EV ---------------------
    # k > 1 → steeper = more weight on cheap sectors → lower EV
    # k < 1 (→ 0) → flatter = more uniform → higher EV (if expensive sectors exist)
    # k = 1 → linear
    k_lo, k_hi = 0.01, 20.0

    _, ev_at_lo = compute_probs_and_ev(k_lo)
    _, ev_at_hi = compute_probs_and_ev(k_hi)

    # Determine search direction
    if ev_at_lo < ev_at_hi:
        # Unusual: higher k gives higher EV (all values roughly equal)
        k_lo, k_hi = k_hi, k_lo
        ev_at_lo, ev_at_hi = ev_at_hi, ev_at_lo

    # Now ev_at_lo >= ev_at_hi (higher k_hi → lower EV)
    # Target: ev_mid.  If both are above or both below, clamp.
    if ev_mid >= ev_at_lo:
        best_k = k_lo
    elif ev_mid <= ev_at_hi:
        best_k = k_hi
    else:
        # Binary search
        lo_k, hi_k = k_lo, k_hi
        for _ in range(200):
            mid_k = (lo_k + hi_k) / 2
            _, ev_at_mid = compute_probs_and_ev(mid_k)
            if abs(ev_at_mid - ev_mid) < 1e-8:
                break
            if ev_at_mid > ev_mid:
                lo_k = mid_k
            else:
                hi_k = mid_k
        best_k = (lo_k + hi_k) / 2

    raw_probs, raw_ev = compute_probs_and_ev(best_k)

    # ---- Round to desired precision using largest-remainder ---------------
    rounded_probs = _largest_remainder_round(raw_probs, budget, precision)

    # Verify sum
    prob_sum = sum(rounded_probs)
    # Fix tiny floating-point drift
    if abs(prob_sum - budget) > precision:
        # Adjust the largest probability
        diff = budget - prob_sum
        max_i = max(range(n), key=lambda i: rounded_probs[i])
        rounded_probs[max_i] += diff

    # Compute final EV with rounded probabilities
    total_ev = fixed_ev + sum(
        rounded_probs[j] * vals[j] for j in range(n)
    ) / 100.0

    # Check if the rounded result is still within the acceptable range
    # If not, try nudging — but the parametric approach should be close enough
    if total_ev < ev_low or total_ev > ev_high:
        # Try a few k adjustments to find one that rounds into range
        found = False
        for offset in [0.01, -0.01, 0.05, -0.05, 0.1, -0.1, 0.5, -0.5]:
            test_k = best_k + offset
            if test_k <= 0:
                continue
            test_raw, _ = compute_probs_and_ev(test_k)
            test_rounded = _largest_remainder_round(test_raw, budget, precision)
            test_ev = fixed_ev + sum(
                test_rounded[j] * vals[j] for j in range(n)
            ) / 100.0
            if ev_low <= test_ev <= ev_high:
                rounded_probs = test_rounded
                total_ev = test_ev
                found = True
                break

        if not found:
            ev_warning = (
                "Rounded probabilities produce EV €%.2f, outside target range "
                "[€%.2f, €%.2f]. Try widening the undershoot range or adjusting "
                "sector values." % (total_ev, ev_low, ev_high)
            )
        else:
            ev_warning = None
    else:
        ev_warning = None

    # ---- Map back to original sector order --------------------------------
    pmap = {active_idx[j]: rounded_probs[j] for j in range(n)}

    result = []
    for i, s in enumerate(sectors):
        prob = fixed.get(i, pmap.get(i, 0.0))
        # Clean up floating point display: round to precision
        prob = round(prob / precision) * precision
        result.append({
            "label": s["label"],
            "value": s["value"],
            "disabled": s.get("disabled", False),
            "probability": prob,
        })

    if ev_warning:
        return result, total_ev, "ok", ev_warning

    return result, total_ev, "ok", ""


# ---------------------------------------------------------------------------
# Output – pretty-printed table
# ---------------------------------------------------------------------------
def _eur(val):
    """Format a EUR value for display."""
    return f"\u20ac{val:.2f}"


def print_wheel_table(name, target, us_min, us_max, sectors, total_ev):
    """Print a formatted table for one wheel to stdout."""
    ev_low = target * (1 - us_max / 100)
    ev_high = target * (1 - us_min / 100)
    undershoot_pct = (1 - total_ev / target) * 100

    w = 78
    print()
    print("=" * w)
    print(f"  {name}")
    print(
        f"  Target: {_eur(target)}  |  "
        f"Acceptable EV: {_eur(ev_low)} - {_eur(ev_high)}  "
        f"(undershoot {us_min}-{us_max}%)"
    )
    print("-" * w)

    # Header
    print(
        f"  {'#':>2}  {'Reward':<14} {'EUR Value':>10}  "
        f"{'Prob':>5}  {'EV Contrib':>11}  {'Cum. EV':>11}"
    )
    print("  " + "-" * (w - 4))

    cum_ev = 0.0
    for i, s in enumerate(sectors, 1):
        ev_c = s["probability"] * s["value"] / 100.0
        cum_ev += ev_c
        tag = " [OFF]" if s["disabled"] else ""
        lbl = s["label"] + tag
        prob_str = f"{s['probability']}%"
        print(
            f"  {i:>2}  {lbl:<14} {_eur(s['value']):>10}  "
            f"{prob_str:>5}  {_eur(ev_c):>11}  {_eur(cum_ev):>11}"
        )

    print("  " + "-" * (w - 4))
    print(f"  Total EV: {_eur(total_ev)}  |  Undershoot: {undershoot_pct:.2f}%")
    print("=" * w)


# ---------------------------------------------------------------------------
# Output – CSV export
# ---------------------------------------------------------------------------
def write_csv(all_results, path="wheels_output.csv"):
    """Write one-row-per-sector CSV for all solved wheels."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Wheel",
                "Sector",
                "Reward",
                "EUR Value",
                "Probability %",
                "EV Contribution",
                "Disabled",
            ]
        )
        for name, sectors in all_results:
            for i, s in enumerate(sectors, 1):
                ev_c = s["probability"] * s["value"] / 100.0
                writer.writerow(
                    [
                        name,
                        i,
                        s["label"],
                        f"{s['value']:.2f}",
                        s["probability"],
                        f"{ev_c:.2f}",
                        "Yes" if s["disabled"] else "No",
                    ]
                )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Bonus wheel probability solver for iGaming CRM"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to a JSON or YAML config file (uses built-in defaults if omitted)",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    all_results = []

    for wheel_cfg in config["wheels"]:
        result_sectors, ev, status, msg = solve_wheel(wheel_cfg)

        name = wheel_cfg["name"]
        target = float(wheel_cfg["target"])
        us_min = float(wheel_cfg["undershoot_min_pct"])
        us_max = float(wheel_cfg["undershoot_max_pct"])

        if status == "ok":
            print_wheel_table(name, target, us_min, us_max, result_sectors, ev)
            all_results.append((name, result_sectors))
        else:
            print()
            print("=" * 78)
            print(f"  {name} — NO VALID SOLUTION")
            print(f"  {msg}")
            print("=" * 78)

    if all_results:
        csv_path = "wheels_output.csv"
        write_csv(all_results, csv_path)
        print(f"\nCSV output written to: {csv_path}")


if __name__ == "__main__":
    main()
