#!/usr/bin/env python3
"""Independent verification of all 5 wheel calculations."""

FS_RATE = 0.10
HB_FS_RATE = 0.25

def val(label):
    """Parse reward label to EUR value."""
    label = label.strip()
    if label.startswith("€"):
        return float(label[1:])
    parts = label.split()
    if "HB" in label:
        num = int(parts[0])
        return num * HB_FS_RATE
    else:
        num = int(parts[0])
        return num * FS_RATE

# Define all 5 wheels exactly as calculated
wheels = [
    {
        "name": "Wheel 1 — €5",
        "target": 5,
        "undershoot_min": 5,
        "undershoot_max": 8,
        "sectors": [
            ("15 HB FS",  3.75,  36.48),
            ("50 FS",     5.00,  26.44),
            ("20 HB FS",  5.00,  17.93),
            ("€5",        5.00,  11.02),
            ("25 HB FS",  6.25,   5.78),
            ("75 FS",     7.50,   2.35),
            ("100 FS",   10.00,   0.00),  # disabled
            ("€10",      10.00,   0.00),  # disabled
        ]
    },
    {
        "name": "Wheel 2 — €10",
        "target": 10,
        "undershoot_min": 5,
        "undershoot_max": 8,
        "sectors": [
            ("25 HB FS",  6.25,  27.84),
            ("75 FS",     7.50,  23.37),
            ("100 FS",   10.00,  18.90),
            ("€10",      10.00,  14.44),
            ("€15",      15.00,   9.96),
            ("75 HB FS", 18.75,   5.49),
            ("€20",      20.00,   0.00),  # disabled
            ("100 HB FS",25.00,   0.00),  # disabled
        ]
    },
    {
        "name": "Wheel 3 — €20",
        "target": 20,
        "undershoot_min": 3,
        "undershoot_max": 4,
        "sectors": [
            ("€15",      15.00,  22.22),
            ("175 FS",   17.50,  20.39),
            ("75 HB FS", 18.75,  18.35),
            ("€20",      20.00,  16.04),
            ("100 HB FS",25.00,  13.29),
            ("€25",      25.00,   9.71),
            ("€30",      30.00,   0.00),  # disabled
            ("€35",      35.00,   0.00),  # disabled
        ]
    },
    {
        "name": "Wheel 4 — €35",
        "target": 35,
        "undershoot_min": 3,
        "undershoot_max": 4,
        "sectors": [
            ("100 HB FS",25.00,  20.38),
            ("€25",      25.00,  19.24),
            ("€30",      30.00,  17.93),
            ("€35",      35.00,  16.37),
            ("€40",      40.00,  14.43),
            ("€60",      60.00,  11.65),
            ("€75",      75.00,   0.00),  # disabled
            ("€80",      80.00,   0.00),  # disabled
        ]
    },
    {
        "name": "Wheel 5 — €65",
        "target": 65,
        "undershoot_min": 2,
        "undershoot_max": 6,
        "sectors": [
            ("100 HB FS",25.00,   0.00),  # disabled
            ("€25",      25.00,   0.00),  # disabled
            ("€30",      30.00,   0.00),  # disabled
            ("€35",      35.00,   0.00),  # disabled
            ("€40",      40.00,  27.78),
            ("€60",      60.00,  26.33),
            ("€75",      75.00,  24.42),
            ("€80",      80.00,  21.47),
        ]
    },
]

all_ok = True
print("=" * 80)
print("  INDEPENDENT VERIFICATION OF ALL 5 WHEELS")
print("=" * 80)

for w in wheels:
    name = w["name"]
    target = w["target"]
    ev_low = target * (1 - w["undershoot_max"] / 100)
    ev_high = target * (1 - w["undershoot_min"] / 100)

    print(f"\n--- {name} ---")
    print(f"  Target: €{target}  |  Acceptable EV: €{ev_low:.2f} – €{ev_high:.2f}")

    # Verify EUR values
    val_errors = []
    for label, eur, prob in w["sectors"]:
        computed = val(label)
        if abs(computed - eur) > 0.01:
            val_errors.append(f"  VALUE ERROR: {label} should be €{computed:.2f}, got €{eur:.2f}")

    if val_errors:
        for e in val_errors:
            print(e)
        all_ok = False
    else:
        print("  ✓ All EUR values correct")

    # Verify probability sum
    active_probs = [p for _, _, p in w["sectors"] if p > 0]
    prob_sum = sum(active_probs)
    if abs(prob_sum - 100.0) > 0.05:
        print(f"  ✗ Probability sum = {prob_sum:.2f}% (should be 100%)")
        all_ok = False
    else:
        print(f"  ✓ Probability sum = {prob_sum:.2f}%")

    # Compute EV
    ev = sum(eur * prob / 100.0 for _, eur, prob in w["sectors"])
    undershoot = (1 - ev / target) * 100

    print(f"  Computed EV: €{ev:.4f}")
    print(f"  Undershoot: {undershoot:.2f}%")

    if ev_low <= ev <= ev_high:
        print(f"  ✓ EV in range")
    else:
        print(f"  ✗ EV OUT OF RANGE")
        all_ok = False

    # Verify all probabilities are non-negative
    neg = [p for _, _, p in w["sectors"] if p < 0]
    if neg:
        print(f"  ✗ Negative probabilities found!")
        all_ok = False

    # Verify probabilities decreasing for active sectors (sorted by value)
    active_sorted = sorted([(eur, prob) for _, eur, prob in w["sectors"] if prob > 0], key=lambda x: x[0])
    mono_ok = True
    for i in range(len(active_sorted) - 1):
        if active_sorted[i+1][1] > active_sorted[i][1] + 0.01:
            mono_ok = False
            break
    if mono_ok:
        print(f"  ✓ Probabilities decrease with increasing value")
    else:
        print(f"  ⚠ Probabilities NOT monotonically decreasing")

    # Detailed EV breakdown
    print(f"\n  {'Label':<14} {'EUR':>8} {'Prob':>8} {'EV Contrib':>12}")
    cumul = 0
    for label, eur, prob in w["sectors"]:
        ev_c = eur * prob / 100.0
        cumul += ev_c
        dis = " (disabled)" if prob == 0 else ""
        print(f"  {label:<14} €{eur:>7.2f} {prob:>7.2f}% €{ev_c:>10.4f}{dis}")
    print(f"  {'':14} {'':>8} {'':>8} €{cumul:>10.4f} TOTAL")

print(f"\n{'='*80}")
if all_ok:
    print("  ✅ ALL WHEELS VERIFIED SUCCESSFULLY")
else:
    print("  ❌ SOME CHECKS FAILED")
print(f"{'='*80}")

# Final summary table
print(f"\n{'='*80}")
print("  SUMMARY TABLE")
print(f"{'='*80}")
print(f"  {'Wheel':<20} {'Target':>8} {'EV':>10} {'Undershoot':>12} {'Active':>8} {'Disabled':>10}")
print(f"  {'-'*70}")
for w in wheels:
    target = w["target"]
    ev = sum(eur * prob / 100.0 for _, eur, prob in w["sectors"])
    undershoot = (1 - ev / target) * 100
    n_active = sum(1 for _, _, p in w["sectors"] if p > 0)
    n_disabled = 8 - n_active
    print(f"  {w['name']:<20} €{target:>6} €{ev:>8.2f} {undershoot:>10.2f}% {n_active:>8} {n_disabled:>10}")
