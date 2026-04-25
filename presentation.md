# Which AI Development Workflow Actually Wins?
**Cubist Hackathon 2026**

---

> [TO FILL: one sentence core finding]

---

## The Question

AI coding tools are everywhere. Nobody agrees on how to use them.

Not which model is best. The workflow: how you structure your interaction
with the model, how much context you provide, how much autonomy you give it,
how you verify its output.

Everyone has opinions. Nobody has data.

So we ran an experiment.

---

## The Experiment

- 10 engines, 10 workflows, same time budget
- Shared base `CLAUDE.md` for standardization
- Single move interface — every engine plugs into the same evaluation system. 
- Results logged automatically, no manual entry

---

## The Workflows

Four philosophies, ten engines.

| Cluster | Engines |
|---|---|
| Basic Prompting | One Shot, Standard Prompting, Phase Implementation |
| Agentic | Adversarial, AutoResearch, Tool-Augmented |
| Data-driven | Stockfish Clone, Large Dataset |
| Unconventional | Tic-Tac-Toe Baseline, Randomized Features |

*Each engine ships with its full `CLAUDE.md` — every prompt, every constraint.*

---

## The Evals

The one shared artifact every engine plugs into equally.

- Fixed time controls enforced externally
- Identical move interface — engine-agnostic
- Illegal moves auto-adjudicated as a loss
- Results logged automatically

**Built by:** [Ishan] — while the other four built engines in parallel.

---

## Results

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

> [TO FILL: one sentence, the core finding]

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

> [TO FILL: 2-3 sentences on what this tells us about AI-assisted development broadly]

---

## The Team

| Member | Engine(s) Owned | Role |
|---|---|---|
| [NAME] | Harness + [engine] | — |
| [NAME] | — | — |
| [NAME] | — | — |
| [NAME] | — | — |
| [NAME] | — | — |
