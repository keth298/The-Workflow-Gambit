# Which AI Development Workflow Actually Wins?
**Cubist Hackathon 2026**

---

## The Question

Everyone uses AI to code. Nobody agrees on how.

We built **12 chess engines** — same problem, same time budget, different workflow each time — then made them fight. The goal wasn't to build a great chess engine. It was to find out which approach to AI-assisted development actually produces the best result, and by what definition of "best."

No single workflow swept. The tradeoffs between strength, cost, and effort are the finding.

---

## Why 12?

We disagreed on the right approach and couldn't resolve it by talking about it.

Should you front-load the model with full context, or let it discover the problem? Does cloning a strong existing engine beat building from scratch? Is a hands-off agentic loop better than careful human steering?

We picked a side on each disagreement, built it, and let the results arbitrate.

---

## The Engines

Each engine ships with the `CLAUDE.md` used to build it.

| Engine | Owner | Going-in Hypothesis | Approach |
|---|---|---|---|
| GAN / Adversarial | — | — | Generate outlandish candidates, adversarially select the best |
| Single Shot | — | — | Standard prompting, no scaffolding |
| Single Shot + Context | — | — | Standard prompting with supplied background knowledge |
| Phase Implementation | — | — | One milestone agent per build stage |
| AutoResearch (Ralphing) | — | — | Hands-off loop, minimal human input |
| Tool-Augmented LLM | — | — | AI with search, databases, and external tools |
| Stockfish Clone (verbatim) | — | — | Reproduce Stockfish directly from source material |
| Stockfish Clone (understood) | — | — | Reproduce Stockfish from human-interpreted understanding |
| Tic-Tac-Toe Baseline | — | — | Intentionally underbuilt, anchors the lower bound |
| Org Structure | — | — | CTO + subagent hires mirroring an engineering org |
| AlphaGo-style | — | — | MCTS + self-play |
| Large Dataset | — | — | Primed with opening books, endgame tables, curated positions |

---

## The Tournament Harness

The harness was the one shared artifact every engine had to plug into equally. All engines expose the same move interface. Time controls are fixed and enforced externally. Illegal moves are auto-adjudicated as a loss. Results log automatically — no manual entry.

**Built by:** —

**Format:**
- Round robin — every engine plays every other, both colors
- Double elimination — bracket seeded from round-robin standings
- Stockfish baseline — all engines play fixed-depth Stockfish to generate a common Elo proxy

---

## Evaluation

### Tournament
| Metric | Format |
|---|---|
| Round robin | Every engine plays every other |
| Double elimination | Bracket to test consistency under pressure |
| Elo rating | Derived from match outcomes |
| Stockfish baseline | Fixed-depth comparison against a known reference |

### Engine Quality
| Metric | Measurement |
|---|---|
| Tactical puzzle accuracy | % correct on a shared curated position set |
| Illegal move rate | Should be 0 — any nonzero is disqualifying |
| Blunder rate | Errors on curated critical positions |
| Avg move time | Seconds per move |

### Workflow Cost
| Metric | Measurement |
|---|---|
| Token cost | Claude Code usage logs (USD) |
| Human time | Hours logged during build |
| Prior knowledge required | Low / Med / High |
| Parallelizability | Could the builder do other work while it ran? |

### Code Quality
| Metric | Measurement |
|---|---|
| Lines of code | Raw size |
| Test coverage | % |
| Creativity | Novelty relative to standard engine design |

---

## Results

### Tournament
| Engine | Round Robin | Double Elim | Elo | vs. Stockfish |
|---|---|---|---|---|
| GAN / Adversarial | — | — | — | — |
| Single Shot | — | — | — | — |
| Single Shot + Context | — | — | — | — |
| Phase Implementation | — | — | — | — |
| AutoResearch | — | — | — | — |
| Tool-Augmented | — | — | — | — |
| Stockfish Clone (verbatim) | — | — | — | — |
| Stockfish Clone (understood) | — | — | — | — |
| Tic-Tac-Toe Baseline | — | — | — | — |
| Org Structure | — | — | — | — |
| AlphaGo-style | — | — | — | — |
| Large Dataset | — | — | — | — |

### Workflow Cost
| Engine | Token Cost | Human Time | Prior Knowledge | Can Do Other Work? |
|---|---|---|---|---|
| GAN / Adversarial | — | — | — | — |
| Single Shot | — | — | — | — |
| Single Shot + Context | — | — | — | — |
| Phase Implementation | — | — | — | — |
| AutoResearch | — | — | — | — |
| Tool-Augmented | — | — | — | — |
| Stockfish Clone (verbatim) | — | — | — | — |
| Stockfish Clone (understood) | — | — | — | — |
| Tic-Tac-Toe Baseline | — | — | — | — |
| Org Structure | — | — | — | — |
| AlphaGo-style | — | — | — | — |
| Large Dataset | — | — | — | — |

---

## Verdict

*To be filled after results.*

The best workflow depends on what you're optimizing for. After results, we'll score each engine on:

- Did it win the tournament?
- Was it the cheapest to run?
- Did it require the least human time and prior knowledge?
- Could the builder do other work while it ran?
- Did it produce clean, testable, documented code?

