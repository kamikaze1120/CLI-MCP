from __future__ import annotations

import logging
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from .sandbox import DockerSandbox
from .security import SecurityChecker

logger = logging.getLogger("cli-mcp.server")


class BearerAuthMiddleware:
    """ASGI middleware that requires 'Authorization: Bearer <token>' on every request."""

    def __init__(self, app: Any, token: str) -> None:
        self.app = app
        self.token = token

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        auth = headers.get(b"authorization", b"").decode("latin-1")

        if auth != f"Bearer {self.token}":
            await send(
                {
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"www-authenticate", b"Bearer"),
                    ],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b'{"error": "unauthorized"}',
                }
            )
            return

        await self.app(scope, receive, send)


def create_server(config: dict[str, Any]) -> FastMCP:
    http_cfg = config.get("server", {}).get("http", {})

    mcp = FastMCP(
        "CLI MCP Gateway",
        instructions=(
            "I can execute CLI commands inside a sandboxed Docker container. "
            "I support any tool installed in the container: git, npm, python, aws, "
            "gcloud, gh, docker, curl, jq, and more. "
            "Use the run_cli tool to execute commands. "
            "Use list_tools to discover what's available."
        ),
        host=http_cfg.get("host", "127.0.0.1"),
        port=http_cfg.get("port", 8080),
    )

    sandbox = DockerSandbox(config)
    security = SecurityChecker(config)

    def effective_timeout(timeout: int) -> int:
        default_timeout = config.get("tools", {}).get("command_timeout", 60)
        max_timeout = config.get("security", {}).get("max_timeout", 300)
        if timeout <= 0:
            timeout = default_timeout
        return min(timeout, max_timeout)

    async def execute(tool: str, args: str, cwd: str, timeout: int) -> str:
        capped_timeout = effective_timeout(timeout)

        security.validate(tool, args, capped_timeout)

        result = await sandbox.exec(
            tool=tool,
            args=args,
            cwd=cwd,
            timeout=capped_timeout,
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
            return await execute(tool, args, cwd, timeout)
        except Exception as e:
            logger.exception("run_cli failed")
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
            logger.exception("list_tools failed")
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
            logger.exception("sandbox_info failed")
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
            logger.exception("reset_sandbox failed")
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
            "python": ("python3", "-c"),
            "node": ("node", "-e"),
            "javascript": ("node", "-e"),
            "bash": ("bash", "-c"),
            "sh": ("sh", "-c"),
        }

        entry = lang_map.get(language.lower())
        if not entry:
            return (
                f"Unsupported language: {language}. "
                f"Supported: {', '.join(lang_map.keys())}"
            )

        interpreter, flag = entry
        escaped_code = code.replace("'", "'\"'\"'")

        try:
            return await execute(
                tool=interpreter,
                args=f"{flag} '{escaped_code}'",
                cwd=cwd,
                timeout=timeout,
            )
        except Exception as e:
            logger.exception("run_script failed")
            return f"Error: {e}"

    return mcp


def run_http(mcp: FastMCP, config: dict[str, Any]) -> None:
    """Serve the MCP server over streamable HTTP, with optional bearer-token auth."""
    import uvicorn

    http_cfg = config.get("server", {}).get("http", {})
    host = http_cfg.get("host", "127.0.0.1")
    port = http_cfg.get("port", 8080)

    app: Any = mcp.streamable_http_app()

    token_env = http_cfg.get("auth_token_env", "CLI_MCP_AUTH_TOKEN")
    token = os.environ.get(token_env, "")

    if token:
        app = BearerAuthMiddleware(app, token)
        logger.info(f"Bearer-token authentication enabled (token from ${token_env}).")
    else:
        logger.warning(
            f"No auth token set (${token_env} is empty) — the HTTP endpoint is UNAUTHENTICATED. "
            "Anyone who can reach it can run commands in the sandbox."
        )

    uvicorn.run(app, host=host, port=port, log_level="info")
