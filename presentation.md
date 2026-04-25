# The Workflow Gambit
**Cubist Hackathon 2026**

---

## Research Question

**What is the most effective software development workflow when using AI as a coding assistant?**

Everyone uses AI. Nobody agrees on how.

- Some engineers don't trust it — holding its hand through every step
- Some describe the problem and walk away
- Some don't even read the output before shipping

---

## Hypothesis

We hypothesized that **more structured, iterative workflows would produce higher-quality output** — and that **more tokens spent and more human involvement would correlate with better results**.

Specifically, we predicted:
- Agentic loops (AutoResearch, Adversarial) would outperform single-shot prompting
- Data-informed approaches (Stockfish Replica, Large Dataset) would produce stronger engines than naive prompting
- Cost and output quality would trend together

We stopped arguing and ran an experiment.

---

## The Setup

- **Controlled variable:** a chess engine — objective win condition, zero ambiguity in output quality
- **Independent variable:** the AI workflow — how each person structured their interaction with Claude
- Every engine started from the same `claude.md` and the same UCI contract
- Every engine plugged into the same evaluation harness
- One person built the harness; four built engines in parallel — nobody on the engine side touched the judge

---

## The 9 Engineering Approaches

**Basic Prompting**

- **Single Shot** — one prompt, one response, no iteration, no correction
- **Standard Prompting** — iterative human steering, step by step, no chess context provided upfront
- **Phased Engine** — discrete milestone phases (move gen → eval → search), each gated before the next begins

**Agent Harnesses**

- **Adversarial** — two agents: one builds, one attacks; output of each becomes input to the other
- **AutoResearch** — write → test → measure → improve loop; set it running and walk away

**Indirect / Creative**

- **Build Up (TicTacToe)** — solve TicTacToe first, extend to checkers, then extend to chess
- **Random Features** — generate a large set of outlandish ideas, let the model self-rank, build the winner

**Data-Driven**

- **Stockfish Replica** — study Stockfish's architecture, explain it in plain language, let the model reimplement it
- **Large Dataset** — feed the model grandmaster games, openings, and puzzles; let pattern exposure drive design

---

## How We Evaluated

Every engine is a black box — the harness only calls the UCI move interface

- **Round-robin** — all 9 engines, 5 games per pair, both colors (40 games per engine)
- **Double-elimination bracket** — seeded from round-robin
- **Stockfish benchmark** — every engine vs. Stockfish at Skill 0, 5, 10, and 20
- Timeouts, crashes, and illegal moves are auto-adjudicated as losses

**Cost tracked per engine:** tokens, API spend, human active time, prompt count, corrections

---

## Cost vs. Rank

```
API Spend vs. Round-Robin Rank
(■ = ~$0.15 | sorted cheapest → most expensive)
──────────────────────────────────────────────────────────
Engine             Spend                  $      Tokens   Time    Rank
──────────────────────────────────────────────────────────
Single Shot        ██░░░░░░░░░░░░░░░░░░  $0.33   45k     15 min   #3
Adversarial        ████░░░░░░░░░░░░░░░░  $0.58   80k     40 min   #1
Standard Prompt    ██████░░░░░░░░░░░░░░  $0.83  115k     25 min   #9
Build Up           ██████░░░░░░░░░░░░░░  $0.92  128k     30 min   #2
Stockfish Replica  ███████░░░░░░░░░░░░░  $1.08  150k     90 min   #6
Large Dataset      ████████░░░░░░░░░░░░  $1.12  155k     40 min   #8
Phased Engine      ████████░░░░░░░░░░░░  $1.21  168k     17 min   #5
Random Features    █████████████░░░░░░░  $1.87  259k    538 min   #4
AutoResearch       ████████████████████  $2.88  400k    150 min   #7
──────────────────────────────────────────────────────────
```

More spend did not produce better results. Adversarial spent 8× less than AutoResearch and finished 6 places higher.

---

## Results

**Round-Robin Standings**

| Rank | Engine | Score | Timeouts | Crashes |
|---|---|---|---|---|
| 1 | Adversarial | **40/40** | 0 | 0 |
| 2 | Build Up | 35/40 | 0 | 0 |
| 3 | Single Shot | 27/40 | 13 | 0 |
| 4 | Random Features | 21/40 | 19 | 0 |
| 5 | Phased Engine | 20/40 | 20 | 0 |
| 6 | Stockfish Replica | 14/40 | 0 | 26 |
| 7 | AutoResearch | 13/40 | 27 | 0 |
| 8 | Large Dataset | 6/40 | 34 | 0 |
| 9 | Standard Prompt | 4/40 | 36 | 0 |

**Adversarial vs. BuildUp (Double-Elim):** both games ended in checkmate — 139 and 110 plies. Not timeouts. Actually playing chess.

**Stockfish Benchmark** (win % across Skill 0–20):
- Single Shot: 50% avg — beat Skill 0 and 5 at 100%, dropped off at Skill 10+
- Build Up: 50% avg — beat Skill 5 and 10 at 100%
- Phased Engine: 37.5% avg
- Standard Prompt: 25% avg

---

## Dimension Winners

| Dimension | Winner | Why |
|---|---|---|
| **Power** | Adversarial | Only engine with zero losses; won bracket by checkmate |
| **Cost** | Single Shot | $0.33, 7–8× cheaper than median, still placed 3rd |
| **Human involvement** | Single Shot | 1 prompt, 0 corrections, 15 min — truly fire and forget |
| **Parallelization** | Single Shot | Stateless, embarrassingly parallel — run 100 concurrently |
| **Simplest code** | Single Shot | Bounded by one response window, cannot sprawl |
| **Most maintainable** | Phased Engine | Five milestone-gated phases enforce explicit interface contracts |

---

## Verdict

**Best engine: Adversarial**

- Perfect 40/40 round-robin record — only engine with zero losses
- Won double-elim bracket via real checkmates
- Cost $0.58 and 40 minutes — second cheapest in the field
- Two adversarial agents is just structured code review: one builds, one attacks, the loop forces improvement
- Every dollar spent on the critic paid off disproportionately in output quality

**Best value: Single Shot**

- $0.33, 1 prompt, 3rd place overall
- The floor of what a single unguided LLM call produces is higher than expected
- This should be the baseline for any AI dev workflow before investing in something more elaborate

**Broader takeaway:** workflow structure mattered more than tokens spent, time invested, or prompts issued

---

## Tradeoff Matrix

| If you're optimizing for... | Use this workflow |
|---|---|
| Strongest output | Adversarial |
| Minimum cost | Single Shot |
| Minimum human time | Single Shot |
| Clean, maintainable code | Phased Engine |
| No domain knowledge required | Single Shot |

---

We went in thinking this was a chess problem.

It turned out to be a workflow problem.

The chess engine was just the test harness.

---

## Live Demo

Open **`demo.html`** in a browser.

- Left panel — **Builder Agent:** generates the engine, applies fixes from each critique round
- Right panel — **Attacker Agent:** probes for weaknesses, returns specific exploits to the builder
- Center — **Chess board** playing a live game as the engine evolves through 5 iterations
- Iteration dots and strength score update in real time as each cycle completes

Click **▶ Start Demo** to run. Click **↺ Reset** to replay.
