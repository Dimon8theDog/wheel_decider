# Wheel Decider

A probability solver and configuration tool for bonus wheel mechanics in iGaming CRM platforms.

Given a set of wheel sectors with reward values and a target bonus cost, the solver finds optimal probability distributions so that the expected value (EV) undershoots the flat bonus by a configurable margin — keeping the wheel profitable while still feeling rewarding to players.

## Features

- **Two solvers**: brute-force integer-percentage solver and a faster parametric power-law solver with decimal precision
- **Interactive GUI** (Tkinter) for designing and tuning wheels in real time
- **Auto-generation** of sector rewards from a single bonus cost + spread slider
- **CSV export** for integration with CRM / game config pipelines
- **JSON/YAML config** support for batch processing multiple wheels via CLI
- **Configurable undershoot range** (default 5–8%) to control house edge

## Quick Start

### GUI

```bash
python wheel_gui.py
```

Enter a bonus cost, adjust the reward spread and sector count, then click **Generate Wheel**. The solver computes probabilities automatically. Use **Export CSV** to save the result.

### CLI

```bash
# Run with built-in default wheels (€5, €10, €20, €35, €65)
python wheel_solver.py

# Run with a custom config
python wheel_solver.py --config wheels.json
```

Output is printed as formatted tables and exported to `wheels_output.csv`.

## Configuration

Each wheel is defined as:

```json
{
  "name": "Wheel 1 - €5",
  "target": 5,
  "undershoot_min_pct": 5,
  "undershoot_max_pct": 8,
  "sectors": [
    {"label": "5 FS",  "value": 1,  "disabled": false},
    {"label": "15 FS", "value": 3,  "disabled": false},
    {"label": "€10",   "value": 10, "disabled": false},
    {"label": "€25",   "value": 25, "disabled": true}
  ]
}
```

| Field | Description |
|---|---|
| `target` | Bonus cost in EUR — the baseline the EV must undershoot |
| `undershoot_min_pct` / `undershoot_max_pct` | Acceptable EV undershoot range (e.g. 5–8% below target) |
| `sectors[].label` | Display name (e.g. "50 FS", "€20") |
| `sectors[].value` | EUR value of the reward |
| `sectors[].disabled` | If `true`, probability is forced to 0% (aspirational prize) |
| `sectors[].locked_probability` | Optional — locks a sector's probability to a fixed value |

Free spins are valued at €0.20 per spin by default.

## How It Works

**Integer solver** (`solve_wheel`): brute-force search over all integer-percentage combinations with branch pruning. Scores solutions by descending probability order, minimum 3% per sector, divisibility by 5, and closeness to the EV midpoint.

**Precise solver** (`solve_wheel_precise`): fits a power-law weight model `w[i] = (n - i)^k` across sectors sorted by value, then binary-searches exponent `k` to hit the target EV. Probabilities are rounded via largest-remainder to preserve the exact sum.

## Dependencies

- Python 3.8+
- `tkinter` (included with most Python installations) — for the GUI
- `pyyaml` (optional) — only needed if using YAML config files

## Project Structure

```
wheel_solver.py   # Core solver logic, CLI entry point, CSV export
wheel_gui.py      # Tkinter GUI wrapping the precise solver
```
