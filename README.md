# The Workflow Gambit

**Cubist Hackathon 2026** — A controlled experiment in AI-assisted software development.

> *5 engineers. 9 workflows. One chess engine specification. Which approach wins?*

---

## The Question

AI coding tools are everywhere. Nobody agrees on how to use them.

Not which model is best — the *workflow*: how you structure your interaction with the model, how much context you provide, how much autonomy you give it, how you verify its output.

Everyone has opinions. Nobody has data.

So we ran an experiment.

---

## The Experiment

We each tried to build a competitive chess engine using Claude — but each person used a completely different prompting and development strategy. Same model, same time budget, same evaluation harness. Nine different workflows.

Each engine had to satisfy one hard constraint: speak **UCI (Universal Chess Interface)**, defined in [`claude.md`](./claude.md). This was the universal contract every engine had to fulfill — move communication, `uci`, `isready`, `go`, `bestmove` — so that all engines could plug into the same automated evaluation framework regardless of how they were built internally.

Engines were then evaluated on chess strength, reliability, engineering quality, and creativity using the framework in [`eval/`](./eval/).

---

## The Approaches

### 1. Adversarial (GAN Structure)
**Owner:** Ethan | **Directory:** [`adversarial/`](./adversarial/)

Two LLM agents work against each other: one builds and improves the engine, one attacks and finds flaws in it. Each agent's output becomes the next agent's input. The engine improves through repeated adversarial cycles — similar in spirit to a GAN.

**Core idea:** Adversarial environments produce stronger output than a single cooperative agent.

| Metric | Value |
|---|---|
| Total tokens | ~80,000 |
| Human time | 40 min |
| Prompts sent | 8 |
| Parallelizable | Partial |

---

### 2. Outlandish Ideas / Random Features
**Owner:** Ethan | **Directory:** [`Random-Features/`](./Random-Features/)

The LLM generates a large set of unconventional engine design ideas, then evaluates and ranks them itself. The single highest-scored idea gets fully built. No human filters the selection — the model both generates and judges.

**Core idea:** Throw a large set of unconventional ideas at the base model and let the strongest one survive.

| Metric | Value |
|---|---|
| Total tokens | ~258,813 |
| Human time | 8h 58m |
| Prompts sent | ~15 |
| Parallelizable | Moderate |

---

### 3. Single Shot
**Owner:** Ethan | **Directory:** [`Single-Shot/`](./Single-Shot/)

One prompt. One response. The entire chess engine is generated in a single LLM call with no follow-up, no iteration, and no correction. What comes out is what gets submitted.

**Core idea:** Be as hands-off as possible. Establish a baseline for zero-effort generation.

| Metric | Value |
|---|---|
| Total tokens | ~45,000 |
| Human time | ~15 min |
| Prompts sent | 1 |
| Parallelizable | Fully |

---

### 4. Standard Prompting
**Owner:** Sachin | **Directory:** [`Standard-Prompt/`](./Standard-Prompt/)

The human iteratively prompts the LLM to build the engine step by step, with no special context or chess knowledge provided upfront. The human steers the conversation based on what the LLM produces, across 6 progressive phases.

**Core idea:** Replicate a basic, non-AI-specialist developer workflow. What does a typical engineer achieve?

| Metric | Value |
|---|---|
| Total tokens | ~115,000 |
| Human time | 25 min |
| Prompts sent | 7 (across 6 phases) |
| Parallelizable | Low |

---

### 5. Phased Engine (Milestone Agents)
**Owner:** JD | **Directory:** [`PhasedEngine/`](./PhasedEngine/)

The engine is built in discrete, predefined phases: move generation, evaluation, search, time management, etc. Each phase is a scoped agent task. No phase begins until the previous one passes a defined milestone check. Phases are documented in [`phase1.md`](./PhasedEngine/phase1.md) through [`phase5.md`](./PhasedEngine/phase5.md).

**Core idea:** Parallelize the work, make it collaborative, and eliminate merge/dependency/refactoring errors through strict phase gating.

| Metric | Value |
|---|---|
| Total tokens | ~168,000 |
| Human time | 17 min |
| Prompts sent | 5 |
| Token breakdown | Planning: 59k · Phase 1: 28.5k · Phase 2: 54.4k · Phase 3: 41.9k · Phase 4: 40.8k |

---

### 6. AutoResearch (Hands-Off Self-Improvement)
**Owner:** JD | **Directory:** [`AutoImprove/`](./AutoImprove/)

The agent runs a fixed loop: write code → test it → measure performance → decide what to change → repeat. The human sets up the loop once and walks away. The engine improves autonomously over a multi-hour run.

**Core idea:** Let the model do everything. Set it running overnight and evaluate what it produces.

| Metric | Value |
|---|---|
| Total tokens | ~400,000 |
| Human time | 2.5 hours |
| Prompts sent | ~20 |
| Parallelizable | Fully (after setup) |

---

### 7. Copy Stockfish (Human-Mediated Knowledge Transfer)
**Owner:** Hyun-Dai | **Directory:** [`StockfishReplica/`](./StockfishReplica/)

A human studies how Stockfish works at a conceptual level — bitboards, alpha-beta pruning, evaluation terms — then explains those concepts to the LLM in plain language. The LLM builds an engine from that understanding. The human is the bridge between Stockfish's architecture and the generated code.

**Core idea:** Replicate expert ideas through human knowledge and prompting rather than relying on the model's own chess intuition. Built in C++.

| Metric | Value |
|---|---|
| Total tokens | ~150,000 |
| Human time | 90 min (hit usage limit) |
| Prompts sent | 1 |
| Language | C++ |
| Notes | Segfaults at depth 6+; capped at depth 5 |

---

### 8. Build Up from Simple (TicTacToe → Chess)
**Owner:** Hyun | **Directory:** [`BuildUpModel-TicTacToe/`](./BuildUpModel-TicTacToe/)

The LLM first builds a working Tic Tac Toe engine, then incrementally expands the logic to checkers, then chess. Each step inherits and extends the previous working structure. Complexity is added only after the simpler game is fully solved.

**Core idea:** Begin with an MVP and slowly add functionality — mirroring real-world incremental software development.

| Metric | Value |
|---|---|
| Total tokens | ~128,000 |
| Human time | ~30 min |
| Prompts sent | 1 |
| Token breakdown | TicTacToe: 25.5k (~6 min) · Checkers: 25.1k (~6 min) · Chess: 77.4k (~18 min) |

---

### 9. Large Dataset (RAG / Pattern Matching)
**Owner:** Team | **Directory:** [`BigDataEngine/`](./BigDataEngine/)

The LLM is given a large body of chess data upfront: openings, grandmaster games, tactical puzzles, endgame tables. It uses this data to inform every design decision. The engine's strength derives from pattern exposure and retrieval-augmented generation rather than hand-coded logic.

**Core idea:** Mirror RAG pipelines. Take advantage of ML's strong pattern-matching capabilities to make a chess bot that learns from data rather than rules.

| Metric | Value |
|---|---|
| Total tokens | ~154,500 |
| Human time | ~40 min |
| Prompts sent | 2 |
| Notes | 15 min model competition + 25 min training & debugging. Requires torch/faiss. |

---

## The Universal Contract: `claude.md`

Every engine, regardless of approach, had to satisfy the UCI protocol. [`claude.md`](./claude.md) was the shared specification file given to every LLM session — it defined the exact UCI handshake requirements (`uci`, `isready`, `uciok`, `readyok`, `go`, `bestmove`) that the evaluation framework expected. This ensured a level playing field: an engine that couldn't speak UCI could not be evaluated, no matter how clever its internals.

---

## Evaluation Framework

The [`eval/`](./eval/) directory contains the full evaluation harness, built independently to remove bias. All engines are treated as black boxes.

Engines compete across five categories:

| Category | Weight |
|---|---|
| Raw Chess Strength | 40% |
| Reliability | 20% |
| Engineering Efficiency | 20% |
| Creativity | 10% |
| Documentation & Reproducibility | 10% |

See [`eval/README.md`](./eval/README.md) for setup instructions and CLI commands.

---

## Repository Structure

```
Point72Hackathon/
  adversarial/          # GAN-style adversarial agent approach
  AutoImprove/          # Hands-off self-improvement loop
  BigDataEngine/        # RAG / large dataset approach
  BuildUpModel-TicTacToe/ # TicTacToe → Checkers → Chess build-up
  PhasedEngine/         # Milestone-gated phase implementation
  Random-Features/      # Outlandish ideas, best-one-wins
  Single-Shot/          # One prompt, one response
  Standard-Prompt/      # Iterative standard prompting
  StockfishReplica/     # Human-mediated Stockfish clone (C++)
  eval/                 # Evaluation framework (engine-agnostic)
  claude.md             # Universal UCI contract given to all sessions
  presentation.md       # Slide deck source
  report.md             # Full written report
```

---

## Quick Comparison

| Approach | Tokens | Human Time | Prompts | Key Trait |
|---|---|---|---|---|
| Single Shot | 45k | 15 min | 1 | Zero iteration |
| Standard Prompting | 115k | 25 min | 7 | Human-guided, iterative |
| Phased Engine | 168k | 17 min | 5 | Structured milestones |
| Build Up | 128k | 30 min | 1 | Incremental complexity |
| Adversarial | 80k | 40 min | 8 | Critic-generator loop |
| Stockfish Replica | 150k | 90 min | 1 | Domain knowledge transfer |
| Big Dataset | 154.5k | 40 min | 2 | RAG / data-driven |
| AutoResearch | 400k | 2.5 hr | ~20 | Fully autonomous |
| Outlandish Ideas | 258.8k | 8h 58m | ~15 | High-variance exploration |

---

## The Team

| Member | Engine(s) | Role |
|---|---|---|
| Ethan | Adversarial, Outlandish Ideas, Single Shot | Engine builder |
| Sachin | Standard Prompting | Engine builder |
| JD | Phased Engine, AutoResearch | Engine builder |
| Hyun-Dai | Stockfish Replica | Engine builder |
| Hyun | Build Up (TicTacToe), Big Dataset | Engine builder |
| Ishan | Evaluation Framework | Harness & judging |
