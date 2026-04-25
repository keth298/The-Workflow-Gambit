import time
from dataclasses import dataclass, field

from engine_tester import EngineTester, TestResult
from test_positions import TEST_POSITIONS
from position_analyzer import random_endgame_positions, pawn_endgame_positions


@dataclass
class RawAttackData:
    iteration: int
    engine_path: str
    results: list[TestResult]
    compliance_ok: bool
    elapsed_s: float


class Attacker:
    def __init__(self, engine_path: str, dynamic_positions: int = 10):
        self.engine_path = engine_path
        self.dynamic_positions = dynamic_positions

    def run(self, iteration: int) -> RawAttackData:
        t0 = time.time()
        tester = EngineTester(self.engine_path)

        compliance_ok = tester.check_uci_compliance()

        dynamic_fens = (
            random_endgame_positions(self.dynamic_positions // 2)
            + pawn_endgame_positions(self.dynamic_positions // 2)
        )
        dynamic = [
            {"name": f"dynamic_{i}", "fen": fen, "expected": "", "depth": 4}
            for i, fen in enumerate(dynamic_fens)
        ]

        all_positions = TEST_POSITIONS + dynamic
        results = tester.run_batch(all_positions)

        return RawAttackData(
            iteration=iteration,
            engine_path=self.engine_path,
            results=results,
            compliance_ok=compliance_ok,
            elapsed_s=time.time() - t0,
        )
