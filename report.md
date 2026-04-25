# Which AI Development Workflow Actually Wins?
**Cubist Hackathon 2026**

---

## The Question

Everyone uses AI to code. Nobody agrees on how.

We built **12 chess engines**, each using a fundamentally different AI-assisted workflow. Same problem. Same time budget. Different process. Then we made them fight.

> **Spoiler: no single workflow sweeps. The tradeoffs between strength, cost, and effort *are* the finding.**

Which workflow produces the best outcome depends entirely on what you're optimizing for — and that's what this report shows.

---

## Why So Many Engines?

We disagreed.

When deciding how to build a chess engine with AI, the team couldn't reach consensus on the right approach. Should you give the model full context upfront or let it discover the problem? Does mimicking an existing strong engine beat building from first principles? Is a hands-off self-improving loop better than careful human steering?

Rather than debate it, we built both sides of every disagreement and let the results decide.

---

## The Engines

Each engine is the artifact of one distinct AI development approach. Every engine ships with the `CLAUDE.md` used to build it.

| Engine | Owner | Going-in Hypothesis | Approach |
|---|---|---|---|
| GAN / Adversarial | — | — | Generate outlandish candidate ideas, adversarially select the best |
| Single Shot | — | — | Standard prompting, no scaffolding |
| Single Shot + Context | — | — | Standard prompting with supplied background knowledge |
| Phase Implementation | — | — | Milestone agents, one per build stage |
| AutoResearch (Ralphing) | — | — | Hands-off, self-improving loop with minimal human input |
| Tool-Augmented LLM | — | — | AI with access to search, databases, and external tools |
| Stockfish Clone (verbatim) | — | — | Reproduce Stockfish logic directly from existing material |
| Stockfish Clone (understood) | — | — | Reproduce Stockfish from human-interpreted understanding |
| Tic-Tac-Toe Baseline | — | — | Intentionally underbuilt reference point to anchor the lower bound |
| Org Structure | — | — | CTO + subagent "hires" mirroring an engineering organization |
| AlphaGo-style | — | — | MCTS + self-play learning approach |
| Large Dataset | — | — | Engine primed with opening books, endgame tables, curated positions |

---

## The Tournament

The tournament harness was a shared collaborative artifact — the one piece every engine had to plug into equally.

**Built by:** —

**Design constraints:**
- All engines expose the same move interface so the harness is engine-agnostic
- Time control is fixed and enforced externally — engines with different move-time profiles compete on equal footing
- Illegal moves are auto-adjudicated as a loss; no manual review
- Match results are logged to a shared results file; no manual entry

**Format:**
- **Round robin** — every engine plays every other, both sides of each pairing
- **Double elimination** — bracket seeded from round-robin results
- **Stockfish baseline** — all engines play a fixed-depth Stockfish reference to generate a common Elo proxy

---

## Evaluation

### Tournament (Raw Power)
| Metric | Format |
|---|---|
| Round robin | Every engine plays every other |
| Double elimination | Bracket to test consistency under pressure |
| Elo-style rating | Derived from match outcomes |
| Stockfish baseline | Fixed-depth comparison against a known reference |

### Engine Quality
| Metric | Measurement |
|---|---|
| Tactical puzzle accuracy | % correct on shared curated position set |
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
| Creativity | Novelty of approach relative to standard engine design |

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

The winning workflow answers **yes** to the most of:
- Did it win the tournament?
- Was it the cheapest to run?
- Did it require the least human time and prior knowledge?
- Could the builder do other work while it ran?
- Did it produce clean, testable, documented code?

**Bonus: Lichess Bot Integration** 🎯
- `lichess_bot.py` - Complete Lichess bot client for real ranked games
- Can earn actual Elo rating by playing against other bots
- Uses proper time controls and handles multiple games simultaneously
- Setup guide: `LICHESS_BOT_SETUP.md`

