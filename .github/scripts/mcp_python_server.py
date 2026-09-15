#!/usr/bin/env python3
"""Simple MCP server for Python code execution in this repo."""

import asyncio
import subprocess
import sys
import os
from pathlib import Path

from mcp.server.models import InitializationOptions
from mcp.server import Server, NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from mcp import types

# Determine repo root (this file is in .github/scripts/)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

server = Server("mark-xxxix-python-runner")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="run_python",
            description="Execute Python code in the repository context. Returns stdout/stderr. Use for running scripts, tools, or quick calculations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute. Can be a single expression or multi-line script.",
                    },
                    "cwd": {
                        "type": "string",
                        "description": f"Working directory for execution. Defaults to repo root: {REPO_ROOT}",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds. Default: 60",
                        "default": 60,
                    },
                },
                "required": ["code"],
            },
        ),
        Tool(
            name="run_script",
            description="Run an existing Python script file within the repo.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative or absolute path to the Python script.",
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Command-line arguments to pass to the script.",
                        "default": [],
                    },
                    "cwd": {
                        "type": "string",
                        "description": f"Working directory. Defaults to repo root: {REPO_ROOT}",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds. Default: 120",
                        "default": 120,
                    },
                },
                "required": ["path"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.Content]:
    if name == "run_python":
        code = arguments["code"]
        cwd = arguments.get("cwd", str(REPO_ROOT))
        timeout = arguments.get("timeout", 60)
        try:
            proc = await asyncio.wait_for(
                asyncio.to_thread(
                    subprocess.run,
                    [sys.executable, "-c", code],
                    capture_output=True,
                    text=True,
                    cwd=cwd,
                    stdin=subprocess.DEVNULL,
                ),
                timeout=timeout,
            )
            result = f"[EXIT CODE: {proc.returncode}]\n\n[STDOUT]\n{proc.stdout}\n\n[STDERR]\n{proc.stderr}"
            return [TextContent(type="text", text=result)]
        except asyncio.TimeoutError:
            return [TextContent(type="text", text=f"[TIMEOUT after {timeout}s]")]
        except Exception as e:
            return [TextContent(type="text", text=f"[ERROR] {e}")]

    elif name == "run_script":
        script_path = arguments["path"]
        args = arguments.get("args", [])
        cwd = arguments.get("cwd", str(REPO_ROOT))
        timeout = arguments.get("timeout", 120)
        target = Path(script_path)
        if not target.is_absolute():
            target = Path(cwd) / script_path
        if not target.exists():
            return [TextContent(type="text", text=f"[ERROR] Script not found: {target}")]
        try:
            proc = await asyncio.wait_for(
                asyncio.to_thread(
                    subprocess.run,
                    [sys.executable, str(target), *args],
                    capture_output=True,
                    text=True,
                    cwd=cwd,
                    stdin=subprocess.DEVNULL,
                ),
                timeout=timeout,
            )
            result = f"[EXIT CODE: {proc.returncode}]\n\n[STDOUT]\n{proc.stdout}\n\n[STDERR]\n{proc.stderr}"
            return [TextContent(type="text", text=result)]
        except asyncio.TimeoutError:
            return [TextContent(type="text", text=f"[TIMEOUT after {timeout}s]")]
        except Exception as e:
            return [TextContent(type="text", text=f"[ERROR] {e}")]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mark-xxxix-python-runner",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
