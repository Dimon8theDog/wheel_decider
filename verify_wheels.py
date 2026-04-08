#!/usr/bin/env python3
"""Independent verification of all 5 wheels. HB FS = 0.50, FS = 0.10."""

FS_RATE = 0.10
HB_FS_RATE = 0.50

def val(label):
    label = label.strip()
    if label.startswith("€"):
        return float(label[1:])
    parts = label.split()
    if "HB" in label:
        return int(parts[0]) * HB_FS_RATE
    else:
        return int(parts[0]) * FS_RATE

wheels = [
    {
        "name": "Wheel 1 — €5",
        "target": 5,
        "undershoot_min": 5,
        "undershoot_max": 8,
        "sectors": [
            ("15 FS",     1.50,  15.94),
            ("25 FS",     2.50,  15.55),
            ("50 FS",     5.00,  15.11),
            ("10 HB FS",  5.00,  14.59),
            ("€5",        5.00,  13.95),
            ("75 FS",     7.50,  13.10),
            ("15 HB FS",  7.50,  11.76),
            ("€10",      10.00,   0.00),
        ]
    },
    {
        "name": "Wheel 2 — €10",
        "target": 10,
        "undershoot_min": 5,
        "undershoot_max": 8,
        "sectors": [
            ("75 FS",     7.50,  19.69),
            ("15 HB FS",  7.50,  18.78),
            ("100 FS",   10.00,  17.73),
            ("€10",      10.00,  16.47),
            ("20 HB FS", 10.00,  14.86),
            ("25 HB FS", 12.50,  12.47),
            ("€15",      15.00,   0.00),
            ("€20",      20.00,   0.00),
        ]
    },
    {
        "name": "Wheel 3 — €20",
        "target": 20,
        "undershoot_min": 3,
        "undershoot_max": 4,
        "sectors": [
            ("25 HB FS", 12.50,  21.97),
            ("€15",      15.00,  20.23),
            ("175 FS",   17.50,  18.30),
            ("€20",      20.00,  16.09),
            ("€25",      25.00,  13.45),
            ("75 HB FS", 37.50,   9.96),
            ("€30",      30.00,   0.00),
            ("€35",      35.00,   0.00),
        ]
    },
    {
        "name": "Wheel 4 — €35",
        "target": 35,
        "undershoot_min": 3,
        "undershoot_max": 4,
        "sectors": [
            ("€25",      25.00,  23.91),
            ("€30",      30.00,  21.36),
            ("€35",      35.00,  18.63),
            ("75 HB FS", 37.50,  15.64),
            ("€40",      40.00,  12.26),
            ("100 HB FS",50.00,   8.20),
            ("€60",      60.00,   0.00),
            ("€75",      75.00,   0.00),
        ]
    },
    {
        "name": "Wheel 5 — €65",
        "target": 65,
        "undershoot_min": 2,
        "undershoot_max": 6,
        "sectors": [
            ("€25",      25.00,   0.00),
            ("€30",      30.00,   0.00),
            ("€35",      35.00,   0.00),
            ("€40",      40.00,   0.00),
            ("100 HB FS",50.00,  35.67),
            ("€60",      60.00,  29.05),
            ("€75",      75.00,  21.80),
            ("€80",      80.00,  13.48),
        ]
    },
]

all_ok = True
print("=" * 80)
print("  INDEPENDENT VERIFICATION — FS=€0.10, HB FS=€0.50")
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

    # Verify probabilities decreasing for active sectors (by value)
    active_sorted = sorted([(eur, prob) for _, eur, prob in w["sectors"] if prob > 0],
                           key=lambda x: x[0])
    mono_ok = all(active_sorted[i][1] >= active_sorted[i+1][1] - 0.01
                  for i in range(len(active_sorted) - 1))
    print(f"  {'✓' if mono_ok else '⚠'} Probabilities {'decrease' if mono_ok else 'NOT monotonically decreasing'} with value")

    # Detailed breakdown
    print(f"\n  {'Label':<14} {'EUR':>8} {'Prob':>8} {'EV Contrib':>12}")
    cumul = 0
    for label, eur, prob in w["sectors"]:
        ev_c = eur * prob / 100.0
        cumul += ev_c
        dis = " (disabled)" if prob == 0 else ""
        print(f"  {label:<14} €{eur:>7.2f} {prob:>7.2f}% €{ev_c:>10.4f}{dis}")
    print(f"  {'':14} {'':>8} {'':>8} €{cumul:>10.4f} TOTAL")

print(f"\n{'='*80}")
print(f"  {'✅ ALL WHEELS VERIFIED' if all_ok else '❌ SOME CHECKS FAILED'}")
print(f"{'='*80}")

# Summary
print(f"\n{'='*80}")
print("  SUMMARY")
print(f"{'='*80}")
print(f"  {'Wheel':<20} {'Target':>8} {'EV':>10} {'Under%':>8} {'Active':>8} {'Fake':>6}")
print(f"  {'-'*62}")
for w in wheels:
    t = w["target"]
    ev = sum(eur * prob / 100.0 for _, eur, prob in w["sectors"])
    u = (1 - ev / t) * 100
    na = sum(1 for _, _, p in w["sectors"] if p > 0)
    print(f"  {w['name']:<20} €{t:>6} €{ev:>8.2f} {u:>7.2f}% {na:>8} {8-na:>6}")
