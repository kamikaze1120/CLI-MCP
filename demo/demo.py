"""Scripted demo: drive the real CLI-MCP server over MCP stdio, exactly like an
AI client does, and print each tool call with its real output.

Used by .github/workflows/demo.yml (recorded with VHS into docs/demo.gif).
Run locally:  python demo/demo.py            (needs Docker + `pip install -e .`)
              python demo/demo.py --warmup   (pull image / start sandbox only)
"""
from __future__ import annotations

import asyncio
import sys
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

DIM, BOLD, RESET = "\033[2m", "\033[1m", "\033[0m"
CYAN, GREEN, RED = "\033[36m", "\033[32m", "\033[31m"

CALLS = [
    ("run_cli", {"tool": "git", "args": "log --oneline -5"}),
    ("run_script", {"language": "bash", "code": (
        "git --version; node --version; python3 --version; go version; "
        "rustc --version; kubectl version --client 2>/dev/null | head -1")}),
    ("run_script", {"language": "python", "code": (
        "import pathlib; files = list(pathlib.Path(\"src\").rglob(\"*.py\")); "
        "print(len(files), \"files,\", sum(len(f.read_text().splitlines()) for f in files), "
        "\"lines of Python in src/\")")}),
    ("run_cli", {"tool": "rm", "args": "-rf /"}),
]


def show_call(name: str, args: dict) -> None:
    rendered = ", ".join(f"{k}={v!r}" for k, v in args.items())
    if len(rendered) > 96:
        rendered = rendered[:93] + "..."
    print(f"{CYAN}▸ {BOLD}{name}{RESET}{CYAN}({rendered}){RESET}", flush=True)


def show_result(text: str) -> None:
    for line in text.rstrip().splitlines():
        color = RED if line.startswith("Error") else DIM if line.startswith("[") else ""
        print(f"  {color}{line}{RESET}", flush=True)
    print(flush=True)


async def main(warmup: bool) -> None:
    params = StdioServerParameters(command="cli-mcp", args=[])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            if warmup:
                await session.call_tool("run_cli", {"tool": "true"})
                return
            tools = await session.list_tools()
            banner = f"{len(tools.tools)} tools · every command runs in a Docker sandbox"
            print(f"{BOLD}MCP client connected to cli-mcp{RESET} {DIM}· {banner}{RESET}\n",
                  flush=True)
            time.sleep(1.2)
            for name, args in CALLS:
                show_call(name, args)
                time.sleep(0.6)
                result = await session.call_tool(name, args)
                show_result("".join(c.text for c in result.content if hasattr(c, "text")))
                time.sleep(1.6)
            repo = "github.com/kamikaze1120/CLI-MCP"
            print(f"{GREEN}✓{RESET} real calls, real output {DIM}· {repo}{RESET}", flush=True)


if __name__ == "__main__":
    asyncio.run(main("--warmup" in sys.argv))
