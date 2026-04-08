#!/usr/bin/env python3
"""
Recalculate Wheels 4 and 5 without 100 HB FS (doesn't exist in pool).

Available HB FS: 10, 15, 20, 25, 75 only.
"""
import math

FS_RATE = 0.10
HB_FS_RATE = 0.50

REWARDS = {
    "15 FS": 1.50, "20 FS": 2.00, "25 FS": 2.50, "50 FS": 5.00,
    "75 FS": 7.50, "100 FS": 10.00, "175 FS": 17.50,
    "10 HB FS": 5.00, "15 HB FS": 7.50, "20 HB FS": 10.00,
    "25 HB FS": 12.50, "75 HB FS": 37.50,
    # NO 100 HB FS!
    "€5": 5, "€10": 10, "€15": 15, "€20": 20, "€25": 25,
    "€30": 30, "€35": 35, "€40": 40, "€60": 60, "€75": 75, "€80": 80,
}

def solve_probabilities(values, target_ev, min_prob=1.0):
    n = len(values)
    if n <= 1:
        return [100.0] if n == 1 and abs(values[0] - target_ev) < 0.01 else None
    budget = 100.0 - n * min_prob
    if budget < 0:
        return None

    def ev_for_k(k):
        weights = [(n - i) ** k for i in range(n)]
        tw = sum(weights)
        probs = [min_prob + budget * (w / tw) for w in weights]
        return sum(p * v / 100.0 for p, v in zip(probs, values)), probs

    ev_steep, _ = ev_for_k(50.0)
    ev_flat, _ = ev_for_k(0.001)
    if target_ev < ev_steep - 0.02 or target_ev > ev_flat + 0.02:
        return None

    k_lo, k_hi = 0.001, 50.0
    for _ in range(500):
        k_mid = (k_lo + k_hi) / 2
        ev_mid, probs = ev_for_k(k_mid)
        if abs(ev_mid - target_ev) < 0.0001:
            break
        if ev_mid > target_ev:
            k_lo = k_mid
        else:
            k_hi = k_mid
    return probs

def round_probs(probs, precision=0.01):
    factor = 1.0 / precision
    target_total = int(round(100.0 * factor))
    scaled = [p * factor for p in probs]
    floored = [int(math.floor(s + 1e-9)) for s in scaled]
    remainders = [(scaled[i] - floored[i], i) for i in range(len(probs))]
    remainders.sort(reverse=True, key=lambda x: x[0])
    deficit = target_total - sum(floored)
    for i in range(max(0, int(deficit))):
        floored[remainders[i][1]] += 1
    result = [f / factor for f in floored]
    diff = 100.0 - sum(result)
    if abs(diff) > 0.001:
        result[max(range(len(result)), key=lambda i: result[i])] += round(diff, 2)
    return result

def design_wheel(name, target, undershoot_min_pct, undershoot_max_pct, sectors):
    ev_low = target * (1 - undershoot_max_pct / 100)
    ev_high = target * (1 - undershoot_min_pct / 100)
    target_ev = (ev_low + ev_high) / 2

    print(f"\n{'='*80}")
    print(f"  {name}")
    print(f"  Target: €{target}  |  Undershoot: {undershoot_min_pct}-{undershoot_max_pct}%")
    print(f"  Acceptable EV: €{ev_low:.2f} – €{ev_high:.2f}  |  Midpoint: €{target_ev:.2f}")
    print(f"{'='*80}")

    active = [(i, l, REWARDS[l]) for i, (l, d) in enumerate(sectors) if not d]
    disabled = [(i, l, REWARDS[l]) for i, (l, d) in enumerate(sectors) if d]

    active_sorted = sorted(active, key=lambda x: x[2])
    active_values = [v for _, _, v in active_sorted]
    avg = sum(active_values) / len(active_values)
    print(f"  Active ({len(active)}), avg = €{avg:.2f}")

    probs = solve_probabilities(active_values, target_ev, min_prob=1.0)
    if probs is None:
        for try_ev in [ev_high - 0.01, ev_low + 0.01]:
            probs = solve_probabilities(active_values, try_ev, min_prob=1.0)
            if probs:
                target_ev = try_ev
                break
    if probs is None:
        print("  *** FAILED ***")
        return

    probs = round_probs(probs)
    prob_map = {orig_i: probs[idx] for idx, (orig_i, _, _) in enumerate(active_sorted)}

    print(f"\n  {'#':<4} {'Reward':<14} {'EUR':>8} {'Dis':>6} {'Prob %':>10} {'EV Contr':>10} {'Cumul EV':>10}")
    print(f"  {'-'*66}")
    cumul = 0
    total_prob = 0
    for i, (label, is_dis) in enumerate(sectors):
        val = REWARDS[label]
        prob = 0.0 if is_dis else prob_map[i]
        total_prob += prob
        ev_c = prob * val / 100
        cumul += ev_c
        d = "☒" if is_dis else "☐"
        print(f"  {i+1:<4} {label:<14} €{val:>7.2f} {d:>6} {prob:>9.2f}% €{ev_c:>8.2f} €{cumul:>8.2f}")

    undershoot = (1 - cumul / target) * 100
    print(f"\n  Total EV: €{cumul:.2f}  |  Undershoot: {undershoot:.2f}%  |  Prob sum: {total_prob:.2f}%")
    ok = ev_low <= cumul <= ev_high
    print(f"  {'✓ PASS' if ok else '✗ FAIL'}")
    return cumul


# ── Wheel 4: €35 — replace 100 HB FS with €60 as active ──
# Active: €25(25), €30(30), €35(35), 75 HB FS(37.50), €40(40), €60(60)
# Avg = 227.5/6 = 37.92 > 33.78 ✓
# Disabled: €75(75), €80(80)
design_wheel("WHEEL 4 — €35 Target (FIXED)", target=35,
    undershoot_min_pct=3, undershoot_max_pct=4,
    sectors=[
        ("€25",       False),  # 25.00
        ("€30",       False),  # 30.00
        ("€35",       False),  # 35.00
        ("75 HB FS",  False),  # 37.50
        ("€40",       False),  # 40.00
        ("€60",       False),  # 60.00
        ("€75",       True),   # 75.00 (fake)
        ("€80",       True),   # 80.00 (fake)
    ])

# ── Wheel 5: €65 — replace 100 HB FS fake with 75 HB FS fake ──
# Active: €40(40), €60(60), €75(75), €80(80)  — same as before
# Avg = 255/4 = 63.75 > 62.40 ✓
# Disabled: 75 HB FS(37.50), €25(25), €30(30), €35(35)
design_wheel("WHEEL 5 — €65 Target (FIXED)", target=65,
    undershoot_min_pct=2, undershoot_max_pct=6,
    sectors=[
        ("75 HB FS",  True),   # 37.50 (fake)
        ("€25",       True),   # 25.00 (fake)
        ("€30",       True),   # 30.00 (fake)
        ("€35",       True),   # 35.00 (fake)
        ("€40",       False),  # 40.00
        ("€60",       False),  # 60.00
        ("€75",       False),  # 75.00
        ("€80",       False),  # 80.00
    ])

# ── Verify unchanged wheels are still correct ──
print("\n\n--- UNCHANGED WHEELS (sanity check) ---")

design_wheel("WHEEL 1 — €5", target=5,
    undershoot_min_pct=5, undershoot_max_pct=8,
    sectors=[
        ("15 FS",     False),
        ("25 FS",     False),
        ("50 FS",     False),
        ("10 HB FS",  False),
        ("€5",        False),
        ("75 FS",     False),
        ("15 HB FS",  False),
        ("€10",       True),
    ])

design_wheel("WHEEL 2 — €10", target=10,
    undershoot_min_pct=5, undershoot_max_pct=8,
    sectors=[
        ("75 FS",     False),
        ("15 HB FS",  False),
        ("100 FS",    False),
        ("€10",       False),
        ("20 HB FS",  False),
        ("25 HB FS",  False),
        ("€15",       True),
        ("€20",       True),
    ])

design_wheel("WHEEL 3 — €20", target=20,
    undershoot_min_pct=3, undershoot_max_pct=4,
    sectors=[
        ("25 HB FS",  False),
        ("€15",       False),
        ("175 FS",    False),
        ("€20",       False),
        ("€25",       False),
        ("75 HB FS",  False),
        ("€30",       True),
        ("€35",       True),
    ])
