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

Five philosophies, ten engines. Each engine ships with the full `CLAUDE.md` 
used to build it — every prompt, every constraint, every correction.

| Philosophy | Engine | Owner | Going-in Hypothesis |
|---|---|---|---|
| Minimal intervention | Single Shot | — | — |
| Minimal intervention | Single Shot + Context | — | — |
| Structured process | Phase Implementation | — | — |
| Structured process | Tool-Augmented | — | — |
| Autonomous / Agentic | AutoResearch | — | — |
| Autonomous / Agentic | Org Structure | — | — |
| Knowledge-first | Stockfish Clone (verbatim) | — | — |
| Knowledge-first | Stockfish Clone (understood) | — | — |
| Knowledge-first | Large Dataset | — | — |
| Adversarial | GAN / Adversarial | — | — |

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
| Engine | Elo | vs. Stockfish | Puzzle Accuracy | Illegal Moves |
|---|---|---|---|---|
| Single Shot | — | — | — | — |
| Single Shot + Context | — | — | — | — |
| Phase Implementation | — | — | — | — |
| AutoResearch | — | — | — | — |
| Tool-Augmented | — | — | — | — |
| GAN / Adversarial | — | — | — | — |
| Org Structure | — | — | — | — |
| Stockfish Clone (verbatim) | — | — | — | — |
| Stockfish Clone (understood) | — | — | — | — |
| Large Dataset | — | — | — | — |

### Workflow Cost
| Engine | Token Cost | Human Time | Prompt Count | Correction Rate | Prior Knowledge | Parallelizable |
|---|---|---|---|---|---|---|
| Single Shot | — | — | — | — | — | — |
| Single Shot + Context | — | — | — | — | — | — |
| Phase Implementation | — | — | — | — | — | — |
| AutoResearch | — | — | — | — | — | — |
| Tool-Augmented | — | — | — | — | — | — |
| GAN / Adversarial | — | — | — | — | — | — |
| Org Structure | — | — | — | — | — | — |
| Stockfish Clone (verbatim) | — | — | — | — | — | — |
| Stockfish Clone (understood) | — | — | — | — | — | — |
| Large Dataset | — | — | — | — | — | — |

### Process Quality
| Engine | Creativity | Avg Move Time | Test Coverage |
|---|---|---|---|
| Single Shot | — | — | — |
| Single Shot + Context | — | — | — |
| Phase Implementation | — | — | — |
| AutoResearch | — | — | — |
| Tool-Augmented | — | — | — |
| GAN / Adversarial | — | — | — |
| Org Structure | — | — | — |
| Stockfish Clone (verbatim) | — | — | — |
| Stockfish Clone (understood) | — | — | — |
| Large Dataset | — | — | — |

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
