"""CLI context object and verbose/retry helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from unity_cli.cli.output import OutputConfig, OutputMode
from unity_cli.client import UnityClient
from unity_cli.config import UnityCLIConfig

# =============================================================================
# Retry Callback
# =============================================================================


def _on_retry_callback(code: str, message: str, attempt: int, backoff_ms: int) -> None:
    """Callback for retry events - outputs to stderr."""
    import sys

    from unity_cli.cli import output

    if output.err_console.no_color:
        print(
            f"[Retry] {code}: {message} (attempt {attempt}, waiting {backoff_ms}ms)",
            file=sys.stderr,
        )
    else:
        output.get_err_console().print(
            f"[dim][Retry][/dim] {code}: {message} (attempt {attempt}, waiting {backoff_ms}ms)",
            style="yellow",
        )


# =============================================================================
# Verbose Helpers
# =============================================================================

_SENSITIVE_KEYS = frozenset({"password", "token", "secret", "apikey", "api_key", "credential"})
_VERBOSE_MAX_LEN = 4096


def _mask_sensitive(obj: Any) -> Any:
    """Recursively mask values whose keys look sensitive."""
    if isinstance(obj, dict):
        return {k: "***" if k.lower() in _SENSITIVE_KEYS else _mask_sensitive(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_mask_sensitive(v) for v in obj]
    return obj


def _truncate_json(text: str) -> str:
    """Truncate JSON string if it exceeds the verbose limit."""
    if len(text) <= _VERBOSE_MAX_LEN:
        return text
    return text[:_VERBOSE_MAX_LEN] + f"... ({len(text)} bytes, truncated)"


def _on_send_verbose(request: dict[str, Any], response: dict[str, Any]) -> None:
    """Callback for --verbose: dump request/response to stderr."""
    import json
    import sys

    req_text = _truncate_json(json.dumps(_mask_sensitive(request), ensure_ascii=False))
    res_text = _truncate_json(json.dumps(_mask_sensitive(response), ensure_ascii=False))
    sys.stderr.write(f">>> {req_text}\n")
    sys.stderr.write(f"<<< {res_text}\n")


# =============================================================================
# Context Object
# =============================================================================


@dataclass
class CLIContext:
    """Context object shared across commands via ctx.obj."""

    config: UnityCLIConfig
    client: UnityClient
    output: OutputConfig = OutputConfig(mode=OutputMode.PRETTY)
