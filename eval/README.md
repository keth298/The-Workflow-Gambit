# Chess Engine Evaluation Framework

A rigorous evaluation framework for comparing AI-agent-built chess engines on
chess strength, reliability, development cost, and creativity.

## Overview

This framework answers the question:
> *Which AI-agent development strategy produces the best chess engine under hackathon constraints, and at what cost in time, tokens, human effort, and maintainability?*

Each submitted engine is treated as a black box that speaks the
[Universal Chess Interface (UCI)](https://www.chessprogramming.org/UCI).
The framework runs tournaments, benchmarks against Stockfish, evaluates tactical
ability, and aggregates everything into a final leaderboard.

---

## Setup

### Prerequisites

- Python 3.10+
- [Stockfish](https://stockfishchess.org/download/) installed and on your `PATH`

### Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

### Verify Stockfish is accessible

```bash
stockfish
# should print "Stockfish <version> ..."
# type quit to exit
```

---

## Project Structure

```
chess_ai_eval/
  evaluator/           # framework source code
    __main__.py        # CLI entry point
    engine_registry.py
    uci_runner.py
    game_runner.py
    round_robin.py
    double_elim.py
    stockfish_eval.py
    tactics_eval.py
    blunder_eval.py
    metrics.py
    report_generator.py
  configs/
    engines.yaml                  # register all engines here
    tournament.yaml               # time controls, games per pair, etc.
    scoring.yaml                  # leaderboard weights
    process_metrics_template.yaml # copy and fill in per engine
    creativity_template.yaml      # copy and fill in per engine
  engines/                        # one subdirectory per submitted engine
    <engine_id>/
      engine.yaml                 # engine registration (optional; can live in configs/engines.yaml)
      main.py                     # or whatever launches the UCI engine
  datasets/
    tactics.yaml                  # 20 tactical puzzles
    curated_positions.yaml        # 15 positions for blunder analysis
  results/
    games/                        # PGN + JSON per game
    tournaments/                  # round-robin and double-elim results
    puzzles/                      # tactics and Stockfish eval outputs
    reports/                      # final HTML/CSV/JSON report
  tests/
    dummy_engines/                # test stub engines
    test_engine_registry.py
    test_uci_runner.py
    test_game_runner.py
```

---

## Registering an Engine

### Option 1 — Central config (`configs/engines.yaml`)

Add an entry under `engines:`:

```yaml
- engine_id: my_engine_v1
  engine_name: My Engine
  strategy_name: Standard Prompting
  owner: YourName
  uci_command: "python engines/my_engine/main.py"
  language: Python
  frameworks:
    - python-chess
  created_from_existing_foundation: false
  stockfish_derived: false
  enabled: true
  notes: "Built with iterative prompting."
```

### Option 2 — Per-engine YAML (`engines/<id>/engine.yaml`)

Create the file directly inside the engine's directory.
The framework auto-discovers it.

### Optional: UCI options

To set engine options at startup (e.g. for Stockfish skill level), add:

```yaml
uci_options:
  Skill Level: "10"
  UCI_LimitStrength: "true"
```

---

## CLI Commands

All commands run from the project root:

```bash
# Validate UCI handshake for all engines
python3 -m evaluator validate-engines --config configs/engines.yaml

# Run round-robin tournament
python3 -m evaluator run-round-robin --config configs/tournament.yaml

# Run double-elimination bracket (optionally seeded from RR results)
python3 -m evaluator run-double-elim --config configs/tournament.yaml \
  --seed-from results/tournaments/round_robin_main.json

# Benchmark against Stockfish
python3 -m evaluator eval-stockfish --config configs/tournament.yaml \
  --scoring configs/scoring.yaml

# Tactical puzzle evaluation
python3 -m evaluator eval-tactics --config configs/tournament.yaml \
  --dataset datasets/tactics.yaml

# Blunder / centipawn-loss evaluation
python3 -m evaluator eval-blunders --config configs/tournament.yaml \
  --dataset datasets/curated_positions.yaml

# Generate final HTML + CSV + JSON report
python3 -m evaluator generate-report --results results/ \
  --scoring configs/scoring.yaml \
  --out results/reports/final_report.html

# Run entire pipeline in one command
python3 -m evaluator run-full-eval --config configs/tournament.yaml
```

---

## Submitting an Engine

Each engine builder must provide:

1. A working UCI engine (`uci_command` in `engine.yaml`).
2. Source code in `engines/<engine_id>/`.
3. A filled-in `process_metrics_<engine_id>.yaml` (copy from
   `configs/process_metrics_template.yaml`) saved to `results/`.
4. A filled-in `creativity_<engine_id>.yaml` (copy from
   `configs/creativity_template.yaml`) saved to `results/`.

Use a timer while building.  Record token usage from your API provider.

---

## Scoring Model

| Category | Weight |
|---|---|
| Raw Chess Strength | 40% |
| Reliability | 20% |
| Engineering Efficiency | 20% |
| Creativity | 10% |
| Documentation & Reproducibility | 10% |

See `configs/scoring.yaml` to adjust weights.

---

## Running the Test Suite

```bash
python3 -m pytest tests/ -v
```

---

## Hardware Controls

For fair comparison, record and fix the following for all tournament games:

| Item | Value |
|---|---|
| CPU | _(fill in)_ |
| RAM | _(fill in)_ |
| OS | _(fill in)_ |
| Python version | _(fill in)_ |
| Stockfish version | `stockfish --version` |
| GPU available | _(yes/no)_ |

---

## Open Questions (from PRD)

1. How many games per pair are feasible under hackathon time constraints?
2. Should Stockfish-derived engines be in their own category?
3. Should engines be allowed to use opening books?
4. How strict is the originality requirement?
5. Should illegal moves forfeit immediately or allow a retry?

---

## License

MIT
