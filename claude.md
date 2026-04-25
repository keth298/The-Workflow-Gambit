# Chess Engine Requirements

Every engine must speak **UCI** so any two can be paired by an arbiter.

## Required UCI commands
- `uci` → `id name ...`, `id author ...`, `uciok`
- `isready` → `readyok`
- `ucinewgame`
- `position [startpos | fen <fen>] [moves ...]`
- `go [wtime/btime/winc/binc/movetime/depth ...]` → `bestmove <move>`
- `quit`

## Move format (UCI long algebraic)
`e2e4`, promotion `e7e8q`, castling as king move (`e1g1`), null `0000`.

## I/O
UCI on stdin/stdout, one line each, flush after every response. Logs to stderr only.

## Off-limits
Do not read, modify, or reference any files under `LLMPlayer/`.

## Developemnt Process
Aim to create the strongest engine possible during planning, development, and implementation, but once the engine is woking, don't try to improve the model much further.
