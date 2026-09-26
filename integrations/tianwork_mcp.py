#!/usr/bin/env python3
"""Minimal stdio MCP bridge for TianWork.Cli.exe.

The bridge intentionally exposes only privacy-reviewed TianWork commands.
Raw activity-events are not exposed because window titles/resources may contain
personal or sensitive information.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

SERVER_NAME = "tianwork-mcp"
SERVER_VERSION = "1.0.0"

DEFAULT_WINDOWS_CLI = (
    Path(os.environ.get("LOCALAPPDATA", ""))
    / "TianWork"
    / "App"
    / "Cli"
    / "TianWork.Cli.exe"
)

TOOLS = [
    {
        "name": "tianwork_health",
        "description": "Check whether TianWork data storage is available.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "tianwork_work_context",
        "description": "Get privacy-filtered TianWork work context for the requested number of days.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "minimum": 1, "maximum": 90, "default": 7}
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "tianwork_dam_evidence",
        "description": "Get structured DAM evidence captured by TianWork.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "minimum": 1, "maximum": 90, "default": 7}
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "tianwork_latest_report",
        "description": "Read the latest TianWork weekly report.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "tianwork_generate_weekly_report",
        "description": "Generate the current TianWork weekly report.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]


def cli_path() -> Path:
    configured = os.environ.get("TIANWORK_CLI_PATH")
    return Path(configured) if configured else DEFAULT_WINDOWS_CLI


def _days(arguments: dict[str, Any] | None) -> int:
    value = (arguments or {}).get("days", 7)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 90:
        raise ValueError("days must be an integer between 1 and 90")
    return value


def command_for_tool(name: str, arguments: dict[str, Any] | None) -> list[str]:
    executable = str(cli_path())
    if name == "tianwork_health":
        return [executable, "health"]
    if name == "tianwork_work_context":
        return [executable, "work-context", str(_days(arguments))]
    if name == "tianwork_dam_evidence":
        return [executable, "dam-evidence", str(_days(arguments))]
    if name == "tianwork_latest_report":
        return [executable, "latest-report"]
    if name == "tianwork_generate_weekly_report":
        return [executable, "generate-weekly-report"]
    raise ValueError(f"unknown tool: {name}")


def run_tianwork(
    name: str,
    arguments: dict[str, Any] | None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    path = cli_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"TianWork CLI not found at {path}. Set TIANWORK_CLI_PATH to the installed executable."
        )

    completed = runner(
        command_for_tool(name, arguments),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown TianWork CLI error"
        raise RuntimeError(f"TianWork CLI exited with code {completed.returncode}: {detail}")

    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("TianWork CLI returned invalid JSON") from exc


def _response(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def handle_message(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")

    if request_id is None:
        return None

    if method == "initialize":
        params = message.get("params") or {}
        return _response(
            request_id,
            {
                "protocolVersion": params.get("protocolVersion", "2025-06-18"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )

    if method == "ping":
        return _response(request_id, {})

    if method == "tools/list":
        return _response(request_id, {"tools": TOOLS})

    if method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments")
        try:
            payload = run_tianwork(name, arguments)
            return _response(
                request_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(payload, ensure_ascii=False, indent=2),
                        }
                    ],
                    "structuredContent": payload,
                    "isError": False,
                },
            )
        except (ValueError, FileNotFoundError, RuntimeError) as exc:
            return _response(
                request_id,
                {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                },
            )

    return _error(request_id, -32601, f"method not found: {method}")


def serve(stdin: Any = sys.stdin, stdout: Any = sys.stdout) -> None:
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
            response = handle_message(message)
        except json.JSONDecodeError:
            response = _error(None, -32700, "parse error")
        except Exception as exc:
            response = _error(None, -32603, f"internal error: {exc}")

        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            stdout.flush()


if __name__ == "__main__":
    serve()
