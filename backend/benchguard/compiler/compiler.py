"""SOP to Procedure IR Compiler with lint feedback retry loop — docs/ARCHITECTURE.md §8."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from typing import Any, Protocol

from pydantic import ValidationError

from benchguard.compiler.lint import LintError, lint_procedure
from benchguard.compiler.prompt import build_compile_messages, build_retry_message
from benchguard.compiler.schema import get_response_format
from benchguard.contracts.ir import Procedure

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class CompileError(Exception):
    def __init__(self, code: str, details: list[str]) -> None:
        self.code = code
        self.details = details
        super().__init__(f"{code}: " + "; ".join(details))


class ModelClient(Protocol):
    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
        model: str = "muse-spark-1.3",
        temperature: float = 0.1,
    ) -> str: ...


class DefaultOpenAIClient:
    def __init__(self, client: Any) -> None:
        self._client = client

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
        model: str = "muse-spark-1.3",
        temperature: float = 0.1,
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format
        resp = await self._client.chat.completions.create(**kwargs)
        return str(resp.choices[0].message.content or "")


async def compile_sop(
    sop_text: str,
    client: ModelClient | None = None,
    max_attempts: int = 3,
    model: str = "muse-spark-1.3",
) -> tuple[Procedure, list[str]]:
    """Compile SOP text into a validated, linted Procedure IR."""
    cleaned_sop = sop_text.strip()
    if not cleaned_sop:
        raise CompileError("EMPTY_INPUT", ["SOP text cannot be empty."])
    if len(cleaned_sop) > 20000:
        raise CompileError(
            "INPUT_TOO_LONG",
            [f"SOP text exceeds 20,000 character limit (length: {len(cleaned_sop)})."],
        )

    sha256 = hashlib.sha256(cleaned_sop.encode("utf-8")).hexdigest()

    if client is None:
        api_key = os.environ.get("MODEL_API_KEY", "").strip()
        if not api_key:
            raise CompileError(
                "NO_API_KEY",
                ["MODEL_API_KEY environment variable is not configured."],
            )
        from openai import AsyncOpenAI

        client = DefaultOpenAIClient(
            AsyncOpenAI(base_url="https://api.meta.ai/v1", api_key=api_key)
        )

    messages = build_compile_messages(cleaned_sop)
    response_format = get_response_format()
    last_errors: list[str] = []

    for attempt in range(1, max_attempts + 1):
        raw_output = await client.chat_completion(
            messages=messages,
            response_format=response_format,
            model=model,
            temperature=0.1,
        )

        data = _extract_json(raw_output)
        if data is None:
            err = "Model output was not valid JSON."
            last_errors = [err]
            messages.append({"role": "assistant", "content": raw_output})
            messages.append(build_retry_message(last_errors))
            continue

        try:
            # Overwrite source metadata
            data["source"] = {"kind": "text", "sha256": sha256}
            proc = Procedure.model_validate(data)
            lint_procedure(proc)
            proc.compile_meta = {
                "model": model,
                "attempts": attempt,
                "warnings": [],
            }
            return proc, []
        except ValidationError as val_err:
            last_errors = [f"{err['loc']}: {err['msg']}" for err in val_err.errors()]
        except LintError as lint_err:
            last_errors = lint_err.details

        # Prepare retry conversation
        messages.append({"role": "assistant", "content": raw_output})
        messages.append(build_retry_message(last_errors))

    raise CompileError("COMPILE_FAILED", last_errors)


def compile_sop_sync(
    sop_text: str,
    client: ModelClient | None = None,
    max_attempts: int = 3,
    model: str = "muse-spark-1.3",
) -> tuple[Procedure, list[str]]:
    """Synchronous wrapper for compile_sop."""
    return asyncio.run(
        compile_sop(
            sop_text=sop_text,
            client=client,
            max_attempts=max_attempts,
            model=model,
        )
    )


def _extract_json(raw: str) -> dict[str, Any] | None:
    match = _JSON_FENCE.search(raw)
    candidate = match.group(1) if match else raw.strip()
    try:
        data = json.loads(candidate)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return None
