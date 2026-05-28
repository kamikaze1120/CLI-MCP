from __future__ import annotations

import logging
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from .sandbox import DockerSandbox
from .security import SecurityChecker

logger = logging.getLogger("cli-mcp.server")


def create_server(config: dict[str, Any]) -> FastMCP:
    mcp = FastMCP(
        "CLI MCP Gateway",
        instructions=(
            "I can execute CLI commands inside a sandboxed Docker container. "
            "I support any tool installed in the container: git, npm, python, aws, gcloud, gh, docker, curl, jq, and more. "
            "Use the run_cli tool to execute commands. Use list_tools to discover what's available."
        ),
    )

    sandbox = DockerSandbox(config)
    security = SecurityChecker(config)
    server_cfg = config.get("server", {})

    @mcp.tool()
    async def run_cli(
        tool: str,
        args: str = "",
        cwd: str = ".",
        timeout: int = 60,
    ) -> str:
        """Execute any CLI command inside the sandboxed Docker container.

        The command runs in an isolated environment with all common dev tools pre-installed.
        Output is returned as text. Use list_tools() to see what's available.

        Args:
            tool: CLI command to run (e.g., git, npm, python3, aws, gh, curl, jq, rg)
            args: Space-separated arguments and flags for the command
            cwd: Working directory relative to the workspace mount point
            timeout: Maximum execution time in seconds (default 60, max 300)
        """
        try:
            tool_cfg = config.get("tools", {})
            effective_timeout = min(timeout, config.get("security", {}).get("max_timeout", 300))
            default_timeout = tool_cfg.get("command_timeout", 60)
            if effective_timeout == 0:
                effective_timeout = default_timeout

            security.validate(tool, args, effective_timeout)

            result = await sandbox.exec(
                tool=tool,
                args=args,
                cwd=cwd,
                timeout=effective_timeout,
            )

            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                if output:
                    output += "\n"
                output += result.stderr

            output = security.truncate_output(output)

            if result.exit_code != 0:
                output += f"\n\n[Exit code: {result.exit_code}]"

            output += f"\n[Duration: {result.duration:.2f}s]"
            return output or "(no output)"

        except Exception as e:
            logger.exception(f"run_cli failed")
            return f"Error: {e}"

    @mcp.tool()
    async def list_tools() -> str:
        """List all CLI tools available in the sandboxed container.

        Returns a categorized list of available commands installed in the
        cli-mcp-tools image, including dev tools, cloud CLIs, and utilities.
        """
        try:
            return await sandbox.list_tools()
        except Exception as e:
            logger.exception(f"list_tools failed")
            return f"Error listing tools: {e}"

    @mcp.tool()
    async def sandbox_info() -> str:
        """Show the current sandbox configuration and container status.

        Returns image name, container state, uptime, workspace mount settings,
        security mode, and timeout limits.
        """
        try:
            return await sandbox.info()
        except Exception as e:
            logger.exception(f"sandbox_info failed")
            return f"Error getting sandbox info: {e}"

    @mcp.tool()
    async def reset_sandbox() -> str:
        """Reset the sandbox container to a clean state.

        Destroys and recreates the Docker container. Use this if the container
        becomes corrupted, runs out of space, or you want a fresh environment.
        """
        try:
            return await sandbox.reset()
        except Exception as e:
            logger.exception(f"reset_sandbox failed")
            return f"Error resetting sandbox: {e}"

    @mcp.tool()
    async def run_script(
        language: str,
        code: str,
        cwd: str = ".",
        timeout: int = 60,
    ) -> str:
        """Execute a short script in the specified language inside the sandbox.

        Supported languages: python, node (JavaScript), bash, sh.

        Args:
            language: Script language (python, node, bash, sh)
            code: The script content to execute
            cwd: Working directory relative to workspace mount point
            timeout: Maximum execution time in seconds
        """
        lang_map = {
            "python": "python3 -c",
            "node": "node -e",
            "javascript": "node -e",
            "bash": "bash -c",
            "sh": "sh -c",
        }

        executor = lang_map.get(language.lower())
        if not executor:
            return (
                f"Unsupported language: {language}. "
                f"Supported: {', '.join(lang_map.keys())}"
            )

        escaped_code = code.replace("'", "'\"'\"'")
        full_args = f"'{escaped_code}'"

        try:
            security.validate(executor.split()[0], full_args, timeout)
        except Exception as e:
            return f"Security check failed: {e}"

        return await run_cli(
            tool=executor.split()[0],
            args=f"{executor.split()[1]} {full_args}" if " " in executor else full_args,
            cwd=cwd,
            timeout=timeout,
        )

    return mcp
