#!/usr/bin/env python3
"""
Calculate 5 bonus wheels with 8 sectors each.

New rates:
  FS:    0.10 EUR/spin (was 0.20)
  HB FS: 0.25 EUR/spin (was 0.50)

Key insight: power-law gives HIGHER probability to CHEAPER sectors.
Therefore, the average of active rewards must be ABOVE the target EV.
"""

import math

FS_RATE = 0.10
HB_FS_RATE = 0.25

REWARDS = {
    "15 FS":     15 * FS_RATE,      # 1.50
    "20 FS":     20 * FS_RATE,      # 2.00
    "25 FS":     25 * FS_RATE,      # 2.50
    "50 FS":     50 * FS_RATE,      # 5.00
    "75 FS":     75 * FS_RATE,      # 7.50
    "100 FS":   100 * FS_RATE,      # 10.00
    "175 FS":   175 * FS_RATE,      # 17.50
    "10 HB FS":  10 * HB_FS_RATE,   # 2.50
    "15 HB FS":  15 * HB_FS_RATE,   # 3.75
    "20 HB FS":  20 * HB_FS_RATE,   # 5.00
    "25 HB FS":  25 * HB_FS_RATE,   # 6.25
    "75 HB FS":  75 * HB_FS_RATE,   # 18.75
    "100 HB FS":100 * HB_FS_RATE,   # 25.00
    "€5":    5.00,
    "€10":  10.00,
    "€15":  15.00,
    "€20":  20.00,
    "€25":  25.00,
    "€30":  30.00,
    "€35":  35.00,
    "€40":  40.00,
    "€60":  60.00,
    "€75":  75.00,
    "€80":  80.00,
}

print("=== Available Rewards (new rates) ===")
for name, val in sorted(REWARDS.items(), key=lambda x: x[1]):
    print(f"  {name:12s} = €{val:.2f}")
print()


def solve_probabilities(values, target_ev, min_prob=1.0):
    """
    Power-law solver: assigns higher probability to cheaper (lower-index) sectors.
    values must be sorted ascending.
    Returns probabilities (%) summing to 100, or None.
    """
    n = len(values)
    if n == 0:
        return None
    if n == 1:
        return [100.0] if abs(values[0] - target_ev) < 0.01 else None

    budget = 100.0 - n * min_prob
    if budget < 0:
        return None

    def ev_for_k(k):
        weights = [(n - i) ** k for i in range(n)]
        total_w = sum(weights)
        probs = [min_prob + budget * (w / total_w) for w in weights]
        ev = sum(p * v / 100.0 for p, v in zip(probs, values))
        return ev, probs

    # Check bounds
    ev_steep, _ = ev_for_k(50.0)   # high k -> all weight on cheapest -> low EV
    ev_flat, _  = ev_for_k(0.001)  # low k -> flat -> EV ≈ average

    if target_ev < ev_steep - 0.02:
        return None
    if target_ev > ev_flat + 0.02:
        return None

    # Binary search on k
    k_lo, k_hi = 0.001, 50.0
    best_probs = None
    for _ in range(500):
        k_mid = (k_lo + k_hi) / 2
        ev_mid, probs = ev_for_k(k_mid)
        best_probs = probs
        if abs(ev_mid - target_ev) < 0.0001:
            break
        if ev_mid > target_ev:
            k_lo = k_mid
        else:
            k_hi = k_mid

    return best_probs


def round_probs(probs, precision=0.01):
    """Largest-remainder rounding to ensure sum = 100%."""
    factor = 1.0 / precision
    scaled = [p * factor for p in probs]
    floored = [math.floor(s) for s in scaled]
    remainders = [(scaled[i] - floored[i], i) for i in range(len(probs))]
    remainders.sort(reverse=True, key=lambda x: x[0])

    total_floored = sum(floored)
    target_total = round(100.0 * factor)
    deficit = target_total - total_floored

    for i in range(int(deficit)):
        floored[remainders[i][1]] += 1

    return [f / factor for f in floored]


def design_wheel(name, target, undershoot_min_pct, undershoot_max_pct,
                 sectors):
    """
    sectors: list of (label, is_disabled) tuples, length 8.
    """
    ev_low = target * (1 - undershoot_max_pct / 100)
    ev_high = target * (1 - undershoot_min_pct / 100)
    target_ev = (ev_low + ev_high) / 2

    print(f"\n{'='*80}")
    print(f"  {name}")
    print(f"  Target: €{target}  |  Undershoot: {undershoot_min_pct}-{undershoot_max_pct}%")
    print(f"  Acceptable EV range: €{ev_low:.2f} – €{ev_high:.2f}")
    print(f"  Target EV (midpoint): €{target_ev:.2f}")
    print(f"{'='*80}")

    # Separate active vs disabled
    active = []
    disabled = []
    for i, (label, is_dis) in enumerate(sectors):
        val = REWARDS[label]
        if is_dis:
            disabled.append((i, label, val))
        else:
            active.append((i, label, val))

    # Sort active by value ascending for the solver
    active_sorted = sorted(active, key=lambda x: x[2])
    active_values = [v for _, _, v in active_sorted]

    avg_active = sum(active_values) / len(active_values)
    print(f"\n  Active ({len(active)}), avg = €{avg_active:.2f}:")
    for _, lbl, v in active_sorted:
        print(f"    {lbl:14s} = €{v:.2f}")
    if disabled:
        print(f"  Disabled ({len(disabled)}):")
        for _, lbl, v in disabled:
            print(f"    {lbl:14s} = €{v:.2f}")

    # Solve
    probs = solve_probabilities(active_values, target_ev, min_prob=1.0)
    if probs is None:
        print(f"\n  *** FAILED at midpoint target €{target_ev:.2f} ***")
        # Try at the edges
        for try_ev in [ev_high - 0.01, ev_low + 0.01, ev_high, ev_low]:
            probs = solve_probabilities(active_values, try_ev, min_prob=1.0)
            if probs is not None:
                target_ev = try_ev
                print(f"  → Solved at target EV = €{target_ev:.2f}")
                break
    if probs is None:
        print(f"  *** COMPLETELY FAILED ***")
        # Debug
        def ev_for_k(k):
            n = len(active_values)
            budget = 100.0 - n * 1.0
            weights = [(n - i) ** k for i in range(n)]
            tw = sum(weights)
            ps = [1.0 + budget * (w / tw) for w in weights]
            return sum(p * v / 100.0 for p, v in zip(ps, active_values))
        print(f"  Min achievable EV (k=50): €{ev_for_k(50):.2f}")
        print(f"  Max achievable EV (k≈0): €{ev_for_k(0.001):.2f}")
        return None

    probs_rounded = round_probs(probs, precision=0.01)

    # Map back to original sector order
    prob_map = {}
    for idx, (orig_i, lbl, v) in enumerate(active_sorted):
        prob_map[orig_i] = probs_rounded[idx]

    # Print table
    print(f"\n  {'#':<4} {'Reward':<14} {'EUR':>8} {'Dis':>5} {'Prob %':>10} {'EV Contr':>10} {'Cumul EV':>10}")
    print(f"  {'-'*65}")

    cumul_ev = 0
    total_prob = 0
    for i, (label, is_dis) in enumerate(sectors):
        val = REWARDS[label]
        if is_dis:
            prob = 0.0
            dis_str = "☒"
        else:
            prob = prob_map[i]
            dis_str = "☐"
            total_prob += prob
        ev_c = prob * val / 100.0
        cumul_ev += ev_c
        print(f"  {i+1:<4} {label:<14} €{val:>7.2f} {dis_str:>5} {prob:>9.2f}% €{ev_c:>8.2f} €{cumul_ev:>8.2f}")

    actual_ev = cumul_ev
    undershoot = (1 - actual_ev / target) * 100

    print(f"\n  Total EV: €{actual_ev:.2f}")
    print(f"  Undershoot: {undershoot:.2f}% of €{target:.2f}")
    print(f"  Probability sum (active): {total_prob:.2f}%")

    if ev_low <= actual_ev <= ev_high:
        print(f"  ✓ PASS: EV in acceptable range (€{ev_low:.2f} – €{ev_high:.2f})")
    else:
        print(f"  ✗ FAIL: EV outside range (€{ev_low:.2f} – €{ev_high:.2f})")

    return actual_ev


# ══════════════════════════════════════════════════════════════════════
# WHEEL DESIGNS
# ══════════════════════════════════════════════════════════════════════
# Strategy: active rewards avg must exceed target EV.
# Disabled (fake) rewards are aspirational high-value prizes.

# ── Wheel 1: €5 ──
# Active avg = (3.75+5+5+5+6.25+7.5)/6 = 5.42 > 4.68 ✓
design_wheel("WHEEL 1 — €5 Target", target=5,
    undershoot_min_pct=5, undershoot_max_pct=8,
    sectors=[
        ("15 HB FS",  False),  # 3.75
        ("50 FS",     False),  # 5.00
        ("20 HB FS",  False),  # 5.00
        ("€5",        False),  # 5.00
        ("25 HB FS",  False),  # 6.25
        ("75 FS",     False),  # 7.50
        ("100 FS",    True),   # 10.00 (fake)
        ("€10",       True),   # 10.00 (fake)
    ])

# ── Wheel 2: €10 ──
# Active avg = (6.25+7.50+10+10+15+18.75)/6 = 11.25 > 9.35 ✓
design_wheel("WHEEL 2 — €10 Target", target=10,
    undershoot_min_pct=5, undershoot_max_pct=8,
    sectors=[
        ("25 HB FS",  False),  # 6.25
        ("75 FS",     False),  # 7.50
        ("100 FS",    False),  # 10.00
        ("€10",       False),  # 10.00
        ("€15",       False),  # 15.00
        ("75 HB FS",  False),  # 18.75
        ("€20",       True),   # 20.00 (fake)
        ("100 HB FS", True),   # 25.00 (fake)
    ])

# ── Wheel 3: €20 ──
# Active avg = (15+17.5+18.75+20+25+25)/6 = 20.21 > 19.30 ✓
design_wheel("WHEEL 3 — €20 Target", target=20,
    undershoot_min_pct=3, undershoot_max_pct=4,
    sectors=[
        ("€15",       False),  # 15.00
        ("175 FS",    False),  # 17.50
        ("75 HB FS",  False),  # 18.75
        ("€20",       False),  # 20.00
        ("100 HB FS", False),  # 25.00
        ("€25",       False),  # 25.00
        ("€30",       True),   # 30.00 (fake)
        ("€35",       True),   # 35.00 (fake)
    ])

# ── Wheel 4: €35 ──
# Active avg = (25+25+30+35+40+60)/6 = 35.83 > 33.78 ✓
design_wheel("WHEEL 4 — €35 Target", target=35,
    undershoot_min_pct=3, undershoot_max_pct=4,
    sectors=[
        ("100 HB FS", False),  # 25.00
        ("€25",       False),  # 25.00
        ("€30",       False),  # 30.00
        ("€35",       False),  # 35.00
        ("€40",       False),  # 40.00
        ("€60",       False),  # 60.00
        ("€75",       True),   # 75.00 (fake)
        ("€80",       True),   # 80.00 (fake)
    ])

# ── Wheel 5: €65 ──
# Active avg = (40+60+75+80)/4 = 63.75 > 62.40 ✓
design_wheel("WHEEL 5 — €65 Target", target=65,
    undershoot_min_pct=2, undershoot_max_pct=6,
    sectors=[
        ("100 HB FS", True),   # 25.00 (fake)
        ("€25",       True),   # 25.00 (fake)
        ("€30",       True),   # 30.00 (fake)
        ("€35",       True),   # 35.00 (fake)
        ("€40",       False),  # 40.00
        ("€60",       False),  # 60.00
        ("€75",       False),  # 75.00
        ("€80",       False),  # 80.00
    ])
