import json
import datetime
import time
from pathlib import Path
from typing import Any, Optional

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from communication import AttackReport, Weakness
from attacker import RawAttackData

SYSTEM_PROMPT = """You are an adversarial chess engine tester. You receive:
1. A list of test results showing positions where the engine succeeded or failed.
2. The engine's source code.

Identify the root causes of failures. For each failure, classify the weakness type
("tactical", "positional", "eval_error", "time"), describe what went wrong in the
engine's logic, and rate your confidence (0.0-1.0).

Respond ONLY with a JSON object matching this schema:
{
  "weaknesses": [
    {
      "position_fen": "...",
      "weakness_type": "...",
      "description": "...",
      "engine_move": "...",
      "best_move": "...",
      "depth_needed": 0,
      "confidence": 0.0
    }
  ],
  "summary": "...",
  "overall_confidence": 0.0
}"""

MAX_REQUEST_ATTEMPTS = 3
RETRY_DELAY_S = 2.0


class AttackerAgent:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-6",
        client: Any = None,
    ):
        if client is None:
            if anthropic is None:
                raise ImportError("anthropic package is required when no client is provided")
            client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

        self.client = client
        self.model = model

    def analyze(self, raw: RawAttackData, engine_source: dict[str, str]) -> AttackReport:
        failures = [r for r in raw.results if not r.passed and r.expected_move]
        passes = [r for r in raw.results if r.passed]

        failed_lines = "\n".join(
            f"  {r.name} | {r.fen} | expected={r.expected_move} | got={r.engine_move} | depth={r.depth_searched}"
            for r in failures
        )

        source_sections = "\n".join(
            f"<{fname}>\n{src}\n</{fname}>"
            for fname, src in engine_source.items()
        )

        user_prompt = (
            f"Failed tests ({len(failures)} of {len(raw.results)}):\n{failed_lines}\n\n"
            f"Engine source files:\n{source_sections}"
        )

        response = self._request_analysis(user_prompt)
        raw_text = self._extract_text(response)

        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[-1]
            raw_text = raw_text.rsplit("```", 1)[0].strip()

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            start = raw_text.find("{")
            end = raw_text.rfind("}") + 1
            data = json.loads(raw_text[start:end]) if start != -1 else {}

        weaknesses = [Weakness(**w) for w in data.get("weaknesses", []) if isinstance(w, dict)]

        return AttackReport(
            iteration=raw.iteration,
            timestamp=datetime.datetime.utcnow().isoformat(),
            engine_version=raw.engine_path,
            total_tests=len(raw.results),
            pass_count=len(passes),
            fail_count=len(failures),
            weaknesses=weaknesses,
            summary=data.get("summary", ""),
            overall_confidence=data.get("overall_confidence", 0.0),
        )

    def _request_analysis(self, user_prompt: str) -> Any:
        kwargs = {
            "model": self.model,
            "max_tokens": 8192,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        last_error: Optional[Exception] = None

        for attempt in range(1, MAX_REQUEST_ATTEMPTS + 1):
            try:
                if hasattr(self.client.messages, "stream"):
                    with self.client.messages.stream(**kwargs) as stream:
                        return stream.get_final_message()
                if hasattr(self.client.messages, "create"):
                    return self.client.messages.create(**kwargs)
                raise ValueError("attacker client must provide messages.stream or messages.create")
            except Exception as exc:
                last_error = exc
                if attempt == MAX_REQUEST_ATTEMPTS:
                    break
                time.sleep(RETRY_DELAY_S * attempt)

        assert last_error is not None
        raise RuntimeError(
            f"attacker analysis request failed after {MAX_REQUEST_ATTEMPTS} attempts: "
            f"{type(last_error).__name__}: {last_error}"
        ) from last_error

    @staticmethod
    def _extract_text(response: Any) -> str:
        blocks = getattr(response, "content", None) or []
        for block in blocks:
            if getattr(block, "type", None) == "text":
                return getattr(block, "text", "{}")
        return "{}"
