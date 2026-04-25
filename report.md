# Methodology — Which AI Development Workflow Actually Wins?
**Cubist Hackathon 2026 — Prinell**

---

## The Question

AI coding tools are everywhere. Nobody agrees on how to use them.

Not which model is best — that conversation is everywhere. We mean the workflow:
how you structure your interaction with the model, how much context you provide,
how much autonomy you give it, how you verify its output.

Everyone has opinions. Nobody has data.

So we ran an experiment.

---

## The Finding

> [TO FILL: one sentence stating the core tradeoff or winner once results are in]

---

## Experiment Design

One problem, one time budget, one shared interface. The only variable was
the workflow used to build each engine.

Standardization was enforced three ways: a shared base CLAUDE.md that every
builder started from, a fixed move interface every engine had to expose, and
a tournament harness that neither knew nor cared how each engine was built.

---

## The Workflows

Four philosophies, ten engines. Each engine ships with the full `CLAUDE.md`
used to build it — every prompt, every constraint, every correction.

### Basic Prompting
Direct, human-steered prompting. The spectrum from least to most structured.

| Engine | Owner | Going-in Hypothesis |
|---|---|---|
| One Shot | — | Minimal prompting produces a functional engine with no scaffolding |
| Standard Prompting | — | Standard iterative prompting with context outperforms one shot |
| Phase Implementation | — | Breaking the build into milestones improves output quality |

### Agentic
Workflows where the model operates with significant autonomy or through
multi-agent architectures.

| Engine | Owner | Going-in Hypothesis |
|---|---|---|
| Adversarial | — | Adversarial selection of generated candidates improves quality |
| AutoResearch | — | A hands-off self-improving loop can match human-steered output |
| Tool-Augmented | — | Giving the model external tools improves output quality |

### Data-driven
Workflows that front-load the model with existing knowledge rather than
building from first principles.

| Engine | Owner | Going-in Hypothesis |
|---|---|---|
| Stockfish Clone | — | Feeding the model existing source material produces a strong engine |
| Large Dataset | — | Priming with opening books and endgame tables improves play quality |

### Unconventional
Workflows that approach the problem indirectly — either by simplifying it
or by sidestepping traditional engine design entirely.

| Engine | Owner | Going-in Hypothesis |
|---|---|---|
| Tic-Tac-Toe Baseline | — | Intentionally underbuilt — anchors the lower bound |
| Randomized Features | — | Randomized design sidesteps standard engine assumptions |

---

## The Tournament Harness

The harness was the team's shared integration artifact and the mechanism
that makes the comparison fair. It knows nothing about how any engine was
built — it only calls the move interface.

**Design constraints:**
- All engines expose an identical move interface
- Time controls are fixed and enforced externally so engines with different
  move-time profiles compete equally
- Illegal moves are auto-adjudicated as a loss, no manual review
- Match results log automatically to a shared results file

**Built by:** [NAME] — while the other four team members built engines
in parallel. This was the clearest example of intelligent work division
in the project.

**Tournament format:**
- Round robin — every engine plays every other, both colors
- Double elimination — bracket seeded from round-robin standings
- Stockfish baseline — all engines play fixed-depth Stockfish for a common Elo proxy

---

## Metrics

### Output Quality
| Metric | Type | Notes |
|---|---|---|
| Elo rating | Objective | Derived from round robin outcomes |
| Round robin record | Objective | W/L/D |
| vs. Stockfish baseline | Objective | Fixed depth, common reference |
| Tactical puzzle accuracy | Objective | % correct on shared curated set |
| Illegal move rate | Objective | Should be 0 — nonzero disqualifies |

### Workflow Cost
| Metric | Type | Notes |
|---|---|---|
| Token cost | Objective | Claude Code usage logs (USD) |
| Human time | Objective | Hours logged per build |
| Prompt count | Objective | Total prompts issued |
| Correction rate | Objective | Times builder had to redirect the model |
| Prior knowledge required | Categorical | Low / Med / High |
| Parallelizable | Binary | Could builder do other work while it ran? |

### Process Quality
| Metric | Type | Notes |
|---|---|---|
| Creativity of approach | Ranked categorical | How novel relative to standard dev practice |
| Avg move time | Objective | Seconds per move |
| Test coverage | Objective | % |

---

## Results

*To be filled after tournament completes.*

### Output Quality
| Engine | Cluster | Elo | vs. Stockfish | Puzzle Accuracy | Illegal Moves |
|---|---|---|---|---|---|
| One Shot | Basic | — | — | — | — |
| Standard Prompting | Basic | — | — | — | — |
| Phase Implementation | Basic | — | — | — | — |
| Adversarial | Agentic | — | — | — | — |
| AutoResearch | Agentic | — | — | — | — |
| Tool-Augmented | Agentic | — | — | — | — |
| Stockfish Clone | Data-driven | — | — | — | — |
| Large Dataset | Data-driven | — | — | — | — |
| Tic-Tac-Toe Baseline | Unconventional | — | — | — | — |
| Randomized Features | Unconventional | — | — | — | — |

### Workflow Cost
| Engine | Token Cost | Human Time | Prompt Count | Correction Rate | Prior Knowledge | Parallelizable |
|---|---|---|---|---|---|---|
| One Shot | — | — | — | — | — | — |
| Standard Prompting | — | — | — | — | — | — |
| Phase Implementation | — | — | — | — | — | — |
| Adversarial | — | — | — | — | — | — |
| AutoResearch | — | — | — | — | — | — |
| Tool-Augmented | — | — | — | — | — | — |
| Stockfish Clone | — | — | — | — | — | — |
| Large Dataset | — | — | — | — | — | — |
| Tic-Tac-Toe Baseline | — | — | — | — | — | — |
| Randomized Features | — | — | — | — | — | — |

### Process Quality
| Engine | Creativity | Avg Move Time | Test Coverage |
|---|---|---|---|
| One Shot | — | — | — |
| Standard Prompting | — | — | — |
| Phase Implementation | — | — | — |
| Adversarial | — | — | — |
| AutoResearch | — | — | — |
| Tool-Augmented | — | — | — |
| Stockfish Clone | — | — | — |
| Large Dataset | — | — | — |
| Tic-Tac-Toe Baseline | — | — | — |
| Randomized Features | — | — | — |

---

## Verdict

*To be filled after results.*

### Scoring rubric

A workflow scores a point for each of the following:
- Highest Elo or top 3 round robin finish
- Lowest token cost
- Lowest human time
- Lowest correction rate
- Highest test coverage

The workflow with the most points is the overall winner. The tradeoff matrix
shows which workflow wins on each dimension independently.

### Rankings
| Rank | Engine | Strongest At |
|---|---|---|
| 1 | — | — |
| 2 | — | — |
| 3 | — | — |

### Tradeoff Matrix
| If you're optimizing for... | Use this workflow |
|---|---|
| Strongest output, have domain knowledge | — |
| Minimum human time | — |
| Minimum token cost | — |
| Running it while doing other work | — |
| Clean, testable code | — |

---

## What We Learned

*To be filled — but the hypothesis going in is that no single workflow sweeps,
and the tradeoffs between autonomy, cost, and output quality are the real finding.*

---

## The Team

| Member | Engine(s) Owned | Going-in Hypothesis |
|---|---|---|
| [NAME] | Harness + [engine] | — |
| [NAME] | — | — |
| [NAME] | — | — |
| [NAME] | — | — |
| [NAME] | — | — |
