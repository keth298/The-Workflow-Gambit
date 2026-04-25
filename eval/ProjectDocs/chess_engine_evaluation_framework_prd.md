# PRD: Chess Engine Evaluation Framework

## 1. Product Overview

### 1.1 Context
Cubist Hackathon prompt: **Develop a chess engine from scratch or on top of existing foundations using AI.**

Rather than submitting a single chess engine, the team will run a controlled experiment: use different AI-agent development strategies to create separate chess engines, then evaluate those engines across standardized technical, competitive, cost, and human-effort metrics.

The evaluation framework is the system that makes this experiment rigorous. It should treat every submitted engine as a black box that speaks the **Universal Chess Interface (UCI)** and can therefore be run through `python-chess`, Lichess-compatible tooling, or other UCI-compatible tournament infrastructure.

### 1.2 Product Goal
Build an evaluation framework that can:

1. Register multiple UCI-compatible chess engines.
2. Run reproducible round-robin and double-elimination tournaments.
3. Benchmark engines against Stockfish baselines.
4. Track illegal move rate, average move time, timeout rate, crash rate, and result statistics.
5. Evaluate chess quality using tactical puzzles and curated positions.
6. Record development-process metrics such as prompts, cost, human time, frustration, prior knowledge, and agent strategy.
7. Produce a final comparison report ranking agent strategies across both chess performance and engineering efficiency.

### 1.3 Core Thesis
The framework is designed to answer:

> Which AI-agent strategy produces the best chess engine under hackathon constraints, and at what cost in time, tokens, human effort, complexity, and maintainability?

The goal is not only to find the strongest chess engine, but to compare **development methodologies**.

---

## 2. Users and Stakeholders

### 2.1 Primary Users
- Hackathon team members building engines using different AI workflows.
- Evaluators responsible for running tournaments and comparing results.
- Judges reviewing the final project and methodology.

### 2.2 Secondary Users
- Future students or developers who want to reproduce the experiment.
- Researchers interested in AI-agent software engineering workflows.

### 2.3 Stakeholder Goals
| Stakeholder | Goal |
|---|---|
| Engine builders | Submit engines that run reliably under UCI |
| Evaluation team | Compare engines fairly and reproducibly |
| Hackathon judges | Understand the novelty and rigor of the experiment |
| Team leads | Identify which agent strategy gave the best return on effort |

---

## 3. Scope

### 3.1 In Scope
The evaluation framework will support:

- Engine registration and metadata collection.
- UCI engine execution through `python-chess`.
- Round-robin tournaments.
- Double-elimination tournaments.
- Stockfish baseline matches.
- Tactical puzzle evaluation.
- Curated-position blunder analysis.
- Illegal move, timeout, crash, and forfeiture tracking.
- Average move-time and inference-time measurement.
- Cost and usage logging.
- Human involvement tracking.
- Prompt count and prompt quality tracking.
- LOC, test count, documentation count, and framework/language metadata.
- Final score aggregation and reporting.

### 3.2 Out of Scope
The framework will not:

- Build the chess engines themselves.
- Require engines to expose internal evaluation logic.
- Require engines to be written in Python.
- Require engines to be original, unless originality is part of a separate scoring category.
- Guarantee perfect Elo estimates from small sample sizes.
- Replace human qualitative judging entirely.

---

## 4. Assumptions

1. Every engine exposes a valid UCI interface.
2. Every engine can be launched from a command-line command.
3. Engines are black boxes; internal code is only inspected for engineering-process metrics such as LOC, tests, and documentation.
4. The main evaluator is written in Python.
5. `python-chess` is used for board state management, UCI communication, move legality validation, PGN generation, and engine orchestration.
6. Stockfish is available locally as a reference engine.
7. All tournament games use identical time controls, hardware, and opening conditions.
8. Human-process metrics are self-reported but stored in a structured format.
9. The evaluation should be reproducible from saved configuration files.

---

## 5. Engine Strategies Being Compared

Each engine corresponds to a distinct AI-agent development strategy.

| Engine Strategy | Description | Experimental Hypothesis |
|---|---|---|
| GAN / Adversarial Agents | One LLM builds, another attacks and finds flaws; outputs feed into each other | Adversarial review improves reliability and chess strength |
| Outlandish Ideas, Single Out Best | LLM generates many unconventional ideas, ranks them, then builds the top idea | Creative ideation may uncover unusual but effective strategies |
| Single Shot | One prompt, one response, no iteration | Minimal human effort may still produce a functioning baseline |
| Standard Prompting | Human iteratively prompts the LLM step by step | Basic human-in-the-loop prompting is a practical default workflow |
| Phase Implementation / Milestone Agents | Engine built in phases: move generation, evaluation, search, etc. | Decoupled milestones reduce integration errors |
| AutoResearch / Hands-Off Self-Improvement | Agent loops through write/test/measure/improve autonomously | Self-improvement may optimize performance with little human intervention |
| LLM with Tool Augmentation | LLM uses code executor, chess validator, and testing tools while building | Tool access reduces hallucination and invalid code |
| Copy Stockfish to a Tee | LLM reads Stockfish and reproduces it closely | Existing expert implementation provides the strongest blueprint |
| Copy Stockfish Framework via Human Understanding | Human explains Stockfish concepts, LLM implements from that explanation | Human abstraction may outperform direct source-copying under constraints |
| Tic Tac Toe → Checkers → Chess | Build simple game engine first, then scale complexity upward | Gradual complexity improves robustness |
| CTO / Hires Subagent Org | Top-level agent spawns specialized subagents | Agent hierarchy simulates real engineering teams |
| AlphaGo / Start Advanced, Work Down | Start with general/advanced game-engine ideas, then adapt to chess | Overgeneralized systems may produce flexible but complex engines |
| Large Dataset / Pattern Exposure | LLM receives openings, games, tactics, and endgame data upfront | Data-rich context improves chess intuition and evaluation quality |

---

## 6. Success Criteria

### 6.1 Minimum Viable Success
The framework is successful if it can:

1. Run at least 4 UCI engines in a round-robin tournament.
2. Run a double-elimination bracket from the same engine pool.
3. Validate every move through `python-chess`.
4. Record PGNs and structured game metadata.
5. Detect crashes, illegal moves, and timeouts.
6. Evaluate every engine on a fixed tactical puzzle set.
7. Export a final CSV or JSON summary.

### 6.2 Strong Success
The framework is strongly successful if it can also:

1. Estimate Elo-style ratings from tournament results.
2. Benchmark engines against multiple Stockfish skill levels.
3. Generate a final leaderboard by multiple categories.
4. Visualize tradeoffs between strength, cost, time, and human involvement.
5. Produce a reproducible final report from a single command.

### 6.3 Stretch Success
The framework reaches stretch success if it can:

1. Run games in parallel safely.
2. Support Lichess bot compatibility.
3. Support live dashboards during tournaments.
4. Auto-generate natural-language summaries of each engine’s strengths and weaknesses.
5. Use LLM-as-a-judge for creativity and prompt-quality scoring with rubric-based justifications.

---

## 7. Core Product Requirements

### 7.1 Engine Registry

The framework must maintain a registry of all submitted engines and their metadata.

Each engine should have an `engine.yaml` or `engine.json` file.

Required fields:

```yaml
engine_id: standard_prompting_v1
engine_name: Standard Prompting Engine
strategy_name: Standard Prompting
owner: Sachin
uci_command: "python engines/standard_prompting/main.py"
language: Python
frameworks:
  - python-chess
created_from_existing_foundation: false
stockfish_derived: false
notes: "Built through iterative human prompting."
```

Optional fields:

```yaml
repo_path: engines/standard_prompting
build_command: "pip install -r requirements.txt"
test_command: "pytest"
license_notes: "Original implementation"
requires_gpu: false
requires_network: false
```

Acceptance criteria:

- The evaluator can load all engines from a directory.
- Invalid or missing engine configs produce clear errors.
- Engines can be enabled or disabled without deleting files.

### 7.2 UCI Compatibility Layer

The framework must communicate with engines through UCI only.

Functional requirements:

- Launch engine process.
- Send `uci` command.
- Confirm `uciok`.
- Send `isready`.
- Confirm `readyok`.
- Send board state using `position`.
- Request move using `go`.
- Parse `bestmove`.
- Validate move legality using `python-chess`.
- Terminate engine cleanly using `quit`.

Failure handling:

- Engine does not launch.
- Engine does not return `uciok`.
- Engine does not return `readyok`.
- Engine returns malformed move.
- Engine returns illegal move.
- Engine exceeds move time.
- Engine crashes mid-game.

Acceptance criteria:

- Every engine receives the same UCI protocol treatment.
- Illegal moves are recorded and result in a forfeit.
- Crashes are recorded and result in a forfeit.
- Timeouts are recorded and result in a forfeit or forced loss according to tournament config.

### 7.3 Game Runner

The framework must run a single chess game between two UCI engines.

Inputs:

- White engine config.
- Black engine config.
- Time control.
- Starting FEN or default starting position.
- Optional opening book line.
- Random seed.

Outputs:

- Result: white win, black win, draw, forfeit, crash, timeout, illegal move.
- PGN.
- Move list.
- Per-move timing.
- Illegal move count.
- Engine stderr/stdout logs.
- Final board state.
- Termination reason.

Game rules:

- Standard chess rules enforced by `python-chess`.
- Draws detected by checkmate, stalemate, insufficient material, repetition, fifty-move rule, or configured max ply.
- Opening positions can be randomized or fixed.

Acceptance criteria:

- The same game config produces reproducible results when deterministic engines are used.
- The runner can save every game to disk as PGN plus metadata JSON.

### 7.4 Round-Robin Tournament

The framework must run every engine against every other engine.

Format:

- For `N` engines, each pair plays `K` games.
- Colors alternate evenly.
- Optional opening positions can be mirrored so each engine plays both sides of the same opening.

Scoring:

- Win: 1 point.
- Draw: 0.5 points.
- Loss: 0 points.
- Illegal move: loss and illegal move recorded.
- Crash: loss and crash recorded.
- Timeout: loss and timeout recorded.

Output:

- Standings table.
- Pairwise results matrix.
- Per-engine win/draw/loss record.
- Color-specific performance.
- Forfeit/crash/timeout table.
- PGN archive.

Acceptance criteria:

- The tournament can be run with one command.
- Partial tournament progress can be resumed.
- Results are saved incrementally after every game.

### 7.5 Double-Elimination Tournament

The framework must run a double-elimination bracket among submitted engines.

Format:

- Every engine starts in the winners bracket.
- First match loss moves engine to losers bracket.
- Second match loss eliminates engine.
- Grand final occurs between winners bracket champion and losers bracket champion.
- Optional bracket reset if losers bracket champion wins the first grand final.

Match structure:

- Single game.
- Best of 3.
- Best of 5.
- Mini-match with alternating colors.

Default: Best of 2 with one game as white and one as black, followed by tie-break if needed.

Tie-break options:

1. Blitz game with reversed colors.
2. Armageddon-style tie-break.
3. Stockfish evaluation of final drawn positions.
4. Higher round-robin seed.

Seeding options:

- Round-robin standings.
- Random seed.
- Manual seed.
- Stockfish baseline score seed.

Output:

- Bracket visualization data.
- Match logs.
- Final placement.
- Upset tracking.
- Elimination reasons.

Acceptance criteria:

- The double-elimination tournament can be generated from round-robin results.
- Bracket state can be resumed after interruption.
- Every match links to underlying PGNs and JSON metadata.

### 7.6 Stockfish Baseline Evaluation

Each engine must be benchmarked against Stockfish at controlled strengths.

Recommended baselines:

- Stockfish depth 1 or skill level 0: beginner baseline.
- Stockfish skill level 5: weak club baseline.
- Stockfish skill level 10: intermediate baseline.
- Stockfish skill level 20 or fixed depth: strong reference baseline.

Metrics:

- Score percentage against each baseline.
- Average centipawn loss compared with Stockfish analysis.
- Blunder rate.
- Tactical accuracy.
- Survival length against strong Stockfish.

Acceptance criteria:

- Each engine plays both colors against every configured Stockfish level.
- Results are separated from peer tournament results.
- Baseline results are used to contextualize raw tournament rankings.

### 7.7 Tactical Puzzle Evaluation

The framework must evaluate engines on a fixed tactical puzzle set.

Puzzle input format:

```yaml
puzzle_id: mate_in_1_001
fen: "6k1/5ppp/8/8/8/8/5PPP/6K1 w - - 0 1"
best_uci_moves:
  - "g6g7"
tags:
  - mate
  - beginner
max_time_ms: 1000
```

Puzzle categories:

- Mate in 1.
- Mate in 2.
- Hanging piece.
- Fork.
- Pin.
- Skewer.
- Back rank tactic.
- Endgame conversion.
- Defensive only move.
- Opening trap avoidance.

Metrics:

- Top-1 accuracy.
- Top-3 accuracy if engine exposes multiple candidate moves.
- Time to solution.
- Category-specific accuracy.
- Illegal/no-move rate.

Acceptance criteria:

- Every engine is tested on the same puzzle set.
- Puzzle results are saved per puzzle and aggregated by category.
- Tactical score is reported separately from tournament score.

### 7.8 Blunder Rate on Curated Positions

The framework must evaluate how often engines make clearly bad moves from known positions.

Method:

1. Ask engine for its best move.
2. Ask Stockfish to evaluate the position before the move.
3. Apply the engine move.
4. Ask Stockfish to evaluate the position after the move.
5. Compute centipawn loss.

Suggested thresholds:

- Inaccuracy: 50–150 centipawn loss.
- Mistake: 150–300 centipawn loss.
- Blunder: 300+ centipawn loss.
- Catastrophic blunder: immediate mate missed or allowed.

Metrics:

- Average centipawn loss.
- Median centipawn loss.
- Blunder rate.
- Catastrophic blunder rate.
- Best-move agreement with Stockfish.

Acceptance criteria:

- Curated position evaluation is deterministic for fixed engine settings.
- Results are stored per position.
- Blunder metric is included in the final comparison report.

### 7.9 Development Process Metrics

The framework must track the cost and process of creating each engine.

| Category | Metric | Type | Collection Method |
|---|---:|---|---|
| Cost | Input tokens | Numeric | Manual or API export |
| Cost | Output tokens | Numeric | Manual or API export |
| Cost | Estimated dollar cost | Numeric | Manual calculation |
| Human involvement | Human time spent | Minutes | Manual timer |
| Human involvement | Number of prompts | Integer | Manual or transcript parser |
| Human involvement | Number of human corrections | Integer | Manual log |
| Prompting | Average prompt quality | 1–5 score | Human or LLM judge |
| Prompting | Prior chess knowledge required | 1–5 score | Human self-report |
| Engineering | Lines of code | Integer | Automated count |
| Engineering | Number of tests | Integer | Automated count |
| Engineering | Documentation length | Integer/words | Automated count |
| Reliability | Test pass rate | Percentage | Automated test command |
| Experience | Frustration | 1–5 score | Human self-report |
| Experience | Ability to multitask | 1–5 score | Human self-report |
| Agent strategy | Parallelization level | 1–5 score | Human or metadata |

Acceptance criteria:

- Every engine has a process log.
- Missing self-reported fields are marked as unknown, not zero.
- Automated metrics are recalculated during final report generation.

### 7.10 Creativity Evaluation

The framework should include a qualitative creativity score for each engine and strategy.

| Dimension | Question | Score |
|---|---|---:|
| Novelty | Is the engine design meaningfully different from a basic minimax engine? | 1–5 |
| Strategic originality | Does it use unusual evaluation/search ideas? | 1–5 |
| Agent-workflow originality | Was the creation method itself creative? | 1–5 |
| Risk-taking | Did the approach attempt something ambitious? | 1–5 |
| Coherence | Are the creative ideas actually integrated into a working engine? | 1–5 |

Suggested creativity score:

```text
Creativity Score =
0.25 * Novelty +
0.20 * Strategic Originality +
0.25 * Agent Workflow Originality +
0.15 * Risk-Taking +
0.15 * Coherence
```

Evaluation method:

1. Human judges using rubric.
2. LLM-as-a-judge using engine README, strategy notes, and code summary.
3. Hybrid approach where LLM provides first-pass scoring and humans audit final scores.

Acceptance criteria:

- Creativity scoring uses a visible rubric.
- Scores include short justifications.
- Creativity is not mixed directly into raw chess-strength ranking unless explicitly configured.

---

## 8. Data Model

### 8.1 Engine Record

```json
{
  "engine_id": "phase_agents_v1",
  "engine_name": "Phase Agents Engine",
  "strategy_name": "Phase Implementation",
  "owner": "JD",
  "uci_command": "python engines/phase_agents/main.py",
  "language": "Python",
  "frameworks": ["python-chess"],
  "created_from_existing_foundation": false,
  "stockfish_derived": false,
  "enabled": true
}
```

### 8.2 Game Record

```json
{
  "game_id": "rr_000123",
  "tournament_id": "round_robin_main",
  "white_engine_id": "standard_prompting_v1",
  "black_engine_id": "single_shot_v1",
  "start_fen": "startpos",
  "result": "1-0",
  "termination": "checkmate",
  "plies": 57,
  "white_illegal_moves": 0,
  "black_illegal_moves": 0,
  "white_time_ms_total": 14500,
  "black_time_ms_total": 15300,
  "white_avg_move_ms": 508,
  "black_avg_move_ms": 527,
  "pgn_path": "results/games/rr_000123.pgn",
  "metadata_path": "results/games/rr_000123.json"
}
```

### 8.3 Tournament Record

```json
{
  "tournament_id": "round_robin_main",
  "type": "round_robin",
  "engines": ["standard_prompting_v1", "single_shot_v1"],
  "time_control": {
    "base_seconds": 60,
    "increment_seconds": 1
  },
  "games_per_pair": 4,
  "random_seed": 42,
  "status": "completed"
}
```

### 8.4 Process Metrics Record

```json
{
  "engine_id": "standard_prompting_v1",
  "input_tokens": 120000,
  "output_tokens": 45000,
  "estimated_cost_usd": 18.75,
  "human_time_minutes": 95,
  "prompt_count": 23,
  "human_correction_count": 8,
  "prior_knowledge_required_score": 3,
  "frustration_score": 2,
  "multitaskability_score": 3,
  "notes": "Most time spent correcting UCI compatibility bugs."
}
```

---

## 9. Metrics and Scoring

### 9.1 Competitive Strength Metrics

| Metric | Definition |
|---|---|
| Round-robin score | Total points from round-robin games |
| Round-robin win rate | Wins / total games |
| Double-elimination placement | Final bracket placement |
| Stockfish score | Score percentage against Stockfish baselines |
| Elo-style rating | Rating estimated from game outcomes |
| Tactical accuracy | Correct best move percentage on puzzle set |
| Average centipawn loss | Mean eval loss against Stockfish best move |
| Blunder rate | Percentage of curated positions with 300+ cp loss |

### 9.2 Reliability Metrics

| Metric | Definition |
|---|---|
| Illegal move rate | Illegal moves / total moves attempted |
| Crash rate | Crashes / games played |
| Timeout rate | Timeouts / games played |
| UCI startup success | Successful launches / attempted launches |
| Completion rate | Games completed without technical forfeiture |

### 9.3 Efficiency Metrics

| Metric | Definition |
|---|---|
| Average move time | Mean time per move |
| P95 move time | 95th percentile move time |
| Nodes per second | Optional, only if engine reports it |
| Memory usage | Optional, if measurable |
| LOC | Source lines of code |
| Test count | Number of unit/integration tests |
| Documentation amount | README/docs word count |

### 9.4 Human and Agent Workflow Metrics

| Metric | Definition |
|---|---|
| Human time | Minutes actively spent by human |
| Prompt count | Number of prompts sent to AI |
| Prompt quality | Rubric score for specificity and usefulness |
| Human correction count | Number of times human had to fix or redirect |
| Prior knowledge required | How much chess/SWE knowledge was needed |
| Frustration score | Subjective difficulty rating |
| Multitaskability | Whether human could do something else while engine was built |
| Parallelization score | Degree of useful concurrent work |

---

## 10. Aggregate Scoring Model

The framework should avoid pretending there is only one “best” engine. Instead, it should produce multiple leaderboards.

### 10.1 Raw Chess Strength Leaderboard

```text
Raw Strength =
0.45 * RoundRobinNormalized +
0.20 * DoubleElimNormalized +
0.20 * StockfishScoreNormalized +
0.15 * TacticalAccuracyNormalized
```

### 10.2 Reliability Leaderboard

```text
Reliability =
0.35 * CompletionRate +
0.25 * (1 - IllegalMoveRate) +
0.20 * (1 - CrashRate) +
0.20 * (1 - TimeoutRate)
```

### 10.3 Engineering Efficiency Leaderboard

```text
Efficiency =
0.30 * StrengthPerDollar +
0.25 * StrengthPerHumanMinute +
0.20 * StrengthPerPrompt +
0.15 * TestPassRate +
0.10 * MaintainabilityScore
```

### 10.4 Creativity Leaderboard
Use the creativity rubric described earlier.

### 10.5 Overall Experimental Winner

```text
Overall Score =
0.40 * RawStrength +
0.20 * Reliability +
0.20 * EngineeringEfficiency +
0.10 * Creativity +
0.10 * DocumentationAndReproducibility
```

The final report should clearly show that different engines may win different categories.

---

## 11. System Architecture

### 11.1 Components

```text
/evaluator
  /configs
    tournament.yaml
    engines.yaml
    scoring.yaml
  /engines
    /single_shot
    /standard_prompting
    /phase_agents
  /datasets
    tactics.yaml
    curated_positions.yaml
    openings.pgn
  /src
    engine_registry.py
    uci_runner.py
    game_runner.py
    round_robin.py
    double_elim.py
    stockfish_eval.py
    tactics_eval.py
    metrics.py
    report_generator.py
  /results
    /games
    /tournaments
    /puzzles
    /reports
```

### 11.2 Data Flow

1. Load engine configs.
2. Validate UCI compatibility.
3. Run health checks.
4. Run tournaments.
5. Run Stockfish baseline evaluation.
6. Run tactical puzzle suite.
7. Run curated-position blunder suite.
8. Collect process metrics.
9. Aggregate scores.
10. Generate final report.

---

## 12. CLI Requirements

The evaluator should support command-line usage.

Example commands:

```bash
python -m evaluator validate-engines --config configs/engines.yaml
python -m evaluator run-round-robin --config configs/tournament.yaml
python -m evaluator run-double-elim --config configs/double_elim.yaml
python -m evaluator eval-tactics --dataset datasets/tactics.yaml
python -m evaluator eval-stockfish --config configs/stockfish.yaml
python -m evaluator generate-report --results results/ --out results/final_report.html
```

Acceptance criteria:

- Every major evaluation step can be run independently.
- The full pipeline can be run from one command.
- Failed games do not destroy the whole tournament.

---

## 13. Reporting Requirements

### 13.1 Final Report Must Include

1. Executive summary.
2. Description of each agent strategy.
3. Round-robin standings.
4. Double-elimination bracket results.
5. Stockfish baseline results.
6. Tactical puzzle results.
7. Blunder analysis.
8. Reliability table.
9. Cost and usage table.
10. Human involvement table.
11. Creativity scores.
12. Engineering metrics.
13. Overall conclusions.
14. Limitations and threats to validity.

### 13.2 Visualizations

Recommended charts:

- Strength vs. cost.
- Strength vs. human time.
- Strength vs. prompt count.
- Reliability vs. creativity.
- Average move time by engine.
- Illegal move/crash/timeout counts.
- Tactical accuracy by category.
- Round-robin pairwise matrix.

### 13.3 Output Formats

- `final_report.html`
- `final_report.pdf`
- `summary.csv`
- `summary.json`
- PGN archive
- Raw logs archive

---

## 14. Experimental Procedure

### 14.1 Universal Engine-Creation Protocol
For each agent strategy:

1. Start with the same universal instruction: “Create the best chess engine possible under this strategy. The final engine must run through the Universal Chess Interface.”
2. Include the shared `claude.md` or equivalent project-memory file.
3. Follow only the assigned strategy.
4. Stop once the engine is functioning under the UCI health check.
5. Record usage before starting another engine.
6. Track human time with a timer.
7. Record number of prompts.
8. Record corrections and interventions.
9. Save final engine code and process notes.

### 14.2 Submission Checklist Per Engine
Each engine must submit:

- UCI launch command.
- Source code.
- README.
- Engine config file.
- Process metrics file.
- Prompt transcript or summary.
- Cost/usage record.
- Human time estimate.
- Known limitations.

---

## 15. Fairness and Reproducibility Controls

### 15.1 Hardware Controls
All engines should run on the same machine or identical machines.

Record:

- CPU.
- RAM.
- OS.
- Python version.
- Stockfish version.
- Any GPU availability.

### 15.2 Time Controls
Use the same time control for all games.

Recommended hackathon default:

```yaml
time_control:
  base_seconds: 30
  increment_seconds: 0.5
  max_move_seconds: 5
```

### 15.3 Opening Controls
To reduce first-move randomness:

- Use a small fixed opening suite.
- Mirror openings with both colors.
- Save opening seed.

### 15.4 Randomness Controls

- Each engine should declare whether it is deterministic.
- Tournament configs should save random seeds.
- Randomized engines should play enough games to reduce noise.

---

## 16. Testing Strategy

### 16.1 Unit Tests

- Engine config parsing.
- UCI command parsing.
- PGN generation.
- Scoring functions.
- Tournament pairing generation.
- Double-elimination bracket transitions.

### 16.2 Integration Tests

- Run two dummy UCI engines against each other.
- Run one dummy engine against Stockfish.
- Simulate illegal move engine.
- Simulate timeout engine.
- Simulate crashing engine.

### 16.3 Golden Tests

- Fixed tournament input should produce expected standings.
- Fixed bracket input should produce expected champion.
- Fixed puzzle set should produce expected accuracy for a mock engine.

### 16.4 Acceptance Test
A full evaluation run over at least 3 toy engines and 1 Stockfish baseline completes successfully and generates report files.

---

## 17. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Engines fail UCI startup | Cannot evaluate | Add pre-tournament validation |
| Engines hang | Tournament stalls | Per-move and per-game timeout guards |
| Small sample sizes distort strength | Misleading rankings | Use multiple games, mirrored openings, and confidence intervals |
| Stockfish-derived engines dominate | Less interesting comparison | Separate raw strength from creativity/originality |
| Self-reported human metrics are noisy | Weak process comparison | Use clear rubrics and require logs |
| LLM-as-judge bias | Unfair creativity scoring | Human audit and rubric transparency |
| Parallel execution causes resource unfairness | Timing distortion | Default to serial games unless carefully isolated |
| Engines use different hardware assumptions | Unfair benchmark | Record environment and standardize runtime |

---

## 18. Milestones

### Milestone 1: Evaluation Harness MVP
- Engine registry.
- UCI validation.
- Single-game runner.
- PGN and JSON output.

### Milestone 2: Tournament Engine
- Round-robin runner.
- Double-elimination bracket runner.
- Resume support.
- Basic standings report.

### Milestone 3: Quality Evaluation
- Stockfish baseline matches.
- Tactical puzzle evaluation.
- Curated blunder analysis.

### Milestone 4: Process Metrics and Reporting
- Cost/time/prompt logging.
- LOC/test/docs counters.
- Creativity rubric.
- Final report generator.

### Milestone 5: Polish and Demo
- Visualizations.
- Bracket display.
- Final narrative.
- Reproducible demo command.

---

## 19. Recommended MVP Implementation Plan

1. Build the UCI runner.
2. Build the game runner.
3. Build round robin.
4. Build double elimination.
5. Add tactical and Stockfish evaluation.
6. Add process metrics.
7. Generate final report.

---

## 20. Demo Narrative

The final presentation should frame the project as:

> We did not just build a chess engine. We built an experiment for measuring how different AI-agent engineering strategies perform when asked to build the same complex system.

Suggested demo flow:

1. Show list of engine strategies.
2. Show UCI compatibility validation.
3. Run or replay a sample game.
4. Show round-robin standings.
5. Show double-elimination bracket.
6. Show Stockfish/tactics results.
7. Show cost vs. strength tradeoff.
8. Reveal which strategy won each category.
9. Conclude with insights about AI-assisted software engineering.

---

## 21. Open Questions

1. How many games per pair are feasible under hackathon time constraints?
2. Should Stockfish-derived engines be separated into their own category?
3. How strict should the originality requirement be?
4. Should human time include only active prompting or also waiting for AI generation?
5. Should engines be allowed to use opening books or precomputed tables?
6. Should internet access be allowed during engine creation?
7. Should AutoResearch be allowed to run longer than human-driven strategies?
8. How much weight should creativity receive in the final score?
9. Should illegal moves immediately forfeit the game or allow one retry?
10. Should final output prioritize a live demo, a report, or a dashboard?

---

## 22. Final Recommendation

For the hackathon, prioritize the following MVP:

1. UCI validation.
2. Round-robin tournament.
3. Double-elimination bracket.
4. Stockfish baseline matches.
5. Tactical puzzle suite.
6. Cost/time/prompt logging.
7. Final leaderboard and report.

This gives the project a strong technical core and a compelling experimental story. The strongest framing is that the team is evaluating **AI-agent software engineering strategies** using chess engines as the benchmark domain.
