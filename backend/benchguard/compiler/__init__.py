"""SOP compiler package — docs/ARCHITECTURE.md §8."""

from benchguard.compiler.compiler import (
    CompileError,
    ModelClient,
    compile_sop,
    compile_sop_sync,
)
from benchguard.compiler.lint import LintError, lint_procedure
from benchguard.compiler.prompt import (
    COMPILER_SYSTEM_PROMPT,
    build_compile_messages,
    build_retry_message,
)
from benchguard.compiler.schema import (
    get_procedure_json_schema,
    get_response_format,
)

__all__ = [
    "COMPILER_SYSTEM_PROMPT",
    "CompileError",
    "LintError",
    "ModelClient",
    "build_compile_messages",
    "build_retry_message",
    "compile_sop",
    "compile_sop_sync",
    "get_procedure_json_schema",
    "get_response_format",
    "lint_procedure",
]
