import datetime
import json
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

from code_patcher import PATCHABLE_FILES
from communication import AttackReport, BuilderPatch
from syntax_validator import validate_patch

PROMPT_PATH = Path(__file__).with_name("builder_prompt.txt")
MAX_REQUEST_ATTEMPTS = 3
RETRY_DELAY_S = 2.0


class BuilderAgent:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-opus-4-6",
        client: Any = None,
        prompt_path: Optional[str] = None,
    ):
        if client is None:
            if anthropic is None:
                raise ImportError("anthropic package is required when no client is provided")
            client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

        self.client = client
        self.model = model
        prompt_file = Path(prompt_path) if prompt_path else PROMPT_PATH
        self.system_prompt = prompt_file.read_text(encoding="utf-8").strip()

    def patch(
        self,
        report: AttackReport,
        engine_source: dict[str, str],
        iteration: int,
    ) -> BuilderPatch:
        user_prompt = self._build_prompt(report, engine_source, iteration)
        response = self._request_patch(user_prompt)

        data = self._parse_response(response)
        code_changes = self._extract_code_changes(data)
        files_modified = self._extract_files_modified(data, code_changes)

        for filename, code in code_changes.items():
            is_valid, error = validate_patch(filename, code)
            if not is_valid:
                raise ValueError(error)

        return BuilderPatch(
            iteration=iteration,
            timestamp=datetime.datetime.utcnow().isoformat(),
            files_modified=files_modified,
            code_changes=code_changes,
            changes_summary=str(data.get("changes_summary", "")),
            reason=str(data.get("reason", "")),
            confidence=float(data.get("confidence", 0.0)),
        )

    def _request_patch(self, user_prompt: str) -> Any:
        kwargs = {
            "model": self.model,
            "max_tokens": 8192,
            "system": self.system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        last_error: Optional[Exception] = None

        for attempt in range(1, MAX_REQUEST_ATTEMPTS + 1):
            try:
                return self.client.messages.create(**kwargs)
            except Exception as exc:
                last_error = exc
                if attempt == MAX_REQUEST_ATTEMPTS:
                    break
                time.sleep(RETRY_DELAY_S * attempt)

        assert last_error is not None
        raise RuntimeError(
            f"builder patch request failed after {MAX_REQUEST_ATTEMPTS} attempts: "
            f"{type(last_error).__name__}: {last_error}"
        ) from last_error

    def _build_prompt(
        self,
        report: AttackReport,
        engine_source: dict[str, str],
        iteration: int,
    ) -> str:
        weaknesses = report.weaknesses or []
        weakness_lines = "\n".join(
            (
                f"- {weakness.weakness_type} | {weakness.description} | "
                f"FEN={weakness.position_fen} | engine_move={weakness.engine_move} | "
                f"best_move={weakness.best_move} | confidence={weakness.confidence:.2f}"
            )
            for weakness in weaknesses
        ) or "- none"

        source_sections = "\n".join(
            f"<{filename}>\n{engine_source[filename]}\n</{filename}>"
            for filename in sorted(PATCHABLE_FILES)
            if filename in engine_source
        )

        return (
            f"Attack report (iteration {iteration}):\n"
            f"Summary: {report.summary}\n"
            f"Overall confidence: {report.overall_confidence}\n\n"
            f"Weaknesses:\n{weakness_lines}\n\n"
            f"Current engine source:\n{source_sections}"
        )

    def _parse_response(self, response: Any) -> dict[str, Any]:
        raw_text = self._extract_text(response).strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[-1]
            raw_text = raw_text.rsplit("```", 1)[0].strip()

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            start = raw_text.find("{")
            end = raw_text.rfind("}") + 1
            if start == -1 or end <= start:
                raise ValueError("builder response did not contain JSON")
            data = json.loads(raw_text[start:end])

        if not isinstance(data, dict):
            raise ValueError("builder response JSON must be an object")
        return data

    @staticmethod
    def _extract_text(response: Any) -> str:
        blocks = getattr(response, "content", None)
        if not blocks:
            raise ValueError("builder response did not include content blocks")

        texts = []
        for block in blocks:
            if getattr(block, "type", None) == "text":
                texts.append(getattr(block, "text", ""))

        if not texts:
            raise ValueError("builder response did not include text content")
        return "\n".join(texts)

    @staticmethod
    def _extract_code_changes(data: dict[str, Any]) -> dict[str, str]:
        raw_changes = data.get("code_changes")
        if not isinstance(raw_changes, dict) or not raw_changes:
            raise ValueError("builder response missing code_changes")

        code_changes: dict[str, str] = {}
        for filename, code in raw_changes.items():
            if filename not in PATCHABLE_FILES:
                raise ValueError(f"builder attempted to modify forbidden file: {filename}")
            if not isinstance(code, str):
                raise ValueError(f"builder patch for {filename} must be a string")
            code_changes[filename] = code

        return code_changes

    @staticmethod
    def _extract_files_modified(
        data: dict[str, Any],
        code_changes: dict[str, str],
    ) -> list[str]:
        raw_files = data.get("files_modified") or list(code_changes.keys())
        if not isinstance(raw_files, list) or any(not isinstance(item, str) for item in raw_files):
            raise ValueError("builder response files_modified must be a list of strings")

        files_modified = []
        for filename in raw_files:
            if filename not in PATCHABLE_FILES:
                raise ValueError(f"builder reported forbidden file: {filename}")
            if filename not in code_changes:
                raise ValueError(f"builder listed {filename} without a matching code change")
            if filename not in files_modified:
                files_modified.append(filename)

        for filename in code_changes:
            if filename not in files_modified:
                files_modified.append(filename)

        return files_modified
