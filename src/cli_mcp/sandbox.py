from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .path_utils import docker_mount_args, is_windows

logger = logging.getLogger("cli-mcp.sandbox")


class SandboxError(Exception):
    pass


@dataclass
class ExecResult:
    stdout: str
    stderr: str
    exit_code: int
    duration: float


async def _communicate_with_timeout(
    proc: asyncio.subprocess.Process, timeout: int
) -> tuple[bytes, bytes]:
    """Wait for a process to finish, killing it if the timeout elapses."""
    try:
        return await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        try:
            await asyncio.wait_for(proc.communicate(), timeout=5)
        except asyncio.TimeoutError:
            pass
        raise


class DockerSandbox:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        sandbox_cfg = config.get("sandbox", {})
        self.image = sandbox_cfg.get("image", "cli-mcp-tools:latest")
        self.container_name = sandbox_cfg.get("container_name", "cli-mcp-sandbox")
        self.persistent = sandbox_cfg.get("persistent", True)
        self.auto_start = sandbox_cfg.get("auto_start", True)
        self.auto_stop = sandbox_cfg.get("auto_stop", False)
        self.volume_mounts = sandbox_cfg.get("volume_mounts", [])
        self.workspace_cfg = sandbox_cfg.get("workspace", {})
        self._container_id: str | None = None

    def _docker_cmd(self) -> str:
        return shutil.which("docker") or "docker"

    async def _run_docker(
        self, args: list[str], timeout: int = 30
    ) -> subprocess.CompletedProcess:
        cmd = [self._docker_cmd()] + args
        logger.debug(f"Running docker: {' '.join(cmd)}")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await _communicate_with_timeout(proc, timeout)
        except asyncio.TimeoutError:
            raise SandboxError(f"Docker command timed out after {timeout}s: {' '.join(cmd)}")

        return subprocess.CompletedProcess(
            args=cmd,
            returncode=proc.returncode or 0,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
        )

    def _build_volume_flags(self) -> list[str]:
        flags: list[str] = []
        for mount in self.volume_mounts:
            host = mount.get("host_path", "")
            container = mount.get("container_path", "")
            ro = mount.get("read_only", False)
            if host and container:
                flags.extend(docker_mount_args(host, container, ro))

        if self.workspace_cfg.get("mount", True):
            host_ws = self.workspace_cfg.get("host_path", "") or str(Path.cwd())
            container_ws = self.workspace_cfg.get("container_path", "/workspace")
            ro = self.workspace_cfg.get("read_only", False)
            flags.extend(docker_mount_args(host_ws, container_ws, ro))

        return flags

    async def ensure_image(self) -> None:
        logger.info(f"Checking for image '{self.image}'...")
        result = await self._run_docker(
            ["image", "inspect", self.image], timeout=30
        )
        if result.returncode != 0:
            logger.info(f"Image '{self.image}' not found. Attempting to pull...")
            result = await self._run_docker(
                ["pull", self.image], timeout=600
            )
            if result.returncode != 0:
                raise SandboxError(
                    f"Failed to pull image '{self.image}'. "
                    f"Build it first: cli-mcp --build-image"
                )

    async def start(self) -> str:
        logger.info(f"Starting sandbox container '{self.container_name}'...")

        await self.ensure_image()

        inspect_result = await self._run_docker(
            ["container", "inspect", self.container_name], timeout=15
        )

        if inspect_result.returncode == 0:
            logger.info(f"Container '{self.container_name}' exists.")
            status_result = await self._run_docker(
                ["container", "inspect", "--format", "{{.State.Status}}", self.container_name],
                timeout=15,
            )
            status = status_result.stdout.strip()

            if status == "running":
                self._container_id = self.container_name
                logger.info("Container is already running.")
                return f"Container '{self.container_name}' is already running ({status})."

            if status == "exited" or status == "created":
                logger.info(f"Container is '{status}'. Starting...")
                await self._run_docker(
                    ["start", self.container_name], timeout=30
                )
                self._container_id = self.container_name
                return f"Container '{self.container_name}' started (was {status})."

        logger.info(f"Creating new container '{self.container_name}'...")
        run_args = [
            "run",
            "-d",
            "--name", self.container_name,
        ]

        run_args.extend(self._build_volume_flags())

        tools_cfg = self.config.get("tools", {})
        env_vars = tools_cfg.get("env", {})
        for k, v in env_vars.items():
            run_args.extend(["-e", f"{k}={v}"])

        run_args.extend([
            self.image,
            "sleep", "infinity",
        ])

        result = await self._run_docker(run_args, timeout=60)
        if result.returncode != 0:
            raise SandboxError(
                f"Failed to create container: {result.stderr or result.stdout}"
            )

        self._container_id = self.container_name
        logger.info(f"Container '{self.container_name}' created.")
        return f"Container '{self.container_name}' created and started."

    async def stop(self) -> str:
        if not await self._exists():
            return "Container does not exist."

        logger.info(f"Stopping container '{self.container_name}'...")
        result = await self._run_docker(
            ["stop", self.container_name], timeout=30
        )
        if result.returncode != 0:
            raise SandboxError(f"Failed to stop container: {result.stderr}")
        return f"Container '{self.container_name}' stopped."

    async def reset(self) -> str:
        logger.info(f"Resetting sandbox container '{self.container_name}'...")
        if await self._exists():
            await self._run_docker(
                ["rm", "-f", self.container_name], timeout=30
            )
        self._container_id = None
        start_msg = await self.start()
        return f"Container reset and restarted.\n{start_msg}"

    async def _exists(self) -> bool:
        result = await self._run_docker(
            ["container", "inspect", self.container_name], timeout=15
        )
        return result.returncode == 0

    async def exec(
        self,
        tool: str,
        args: str,
        cwd: str = ".",
        timeout: int = 60,
    ) -> ExecResult:
        if not self._container_id:
            if self.auto_start:
                await self.start()
            else:
                raise SandboxError("Sandbox not started. Call start() first.")

        container_ws = self.workspace_cfg.get("container_path", "/workspace")
        workdir = os.path.join(container_ws, cwd).replace("\\", "/") if cwd else container_ws

        if is_windows():
            workdir = workdir.replace("\\", "/")

        exec_cmd = [self._docker_cmd(), "exec", "-i"]
        exec_cmd.extend(["-w", workdir])
        exec_cmd.append(self.container_name)

        alias_map = self.config.get("tools", {}).get("tool_aliases", {})
        actual_tool = alias_map.get(tool, tool)

        shell_cmd = f"{actual_tool} {args}"
        exec_cmd.extend(["/bin/bash", "-c", shell_cmd])

        logger.debug(f"Exec in container: {' '.join(exec_cmd)}")

        start = time.monotonic()

        proc = await asyncio.create_subprocess_exec(
            *exec_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await _communicate_with_timeout(proc, timeout)
        except asyncio.TimeoutError:
            return ExecResult(
                stdout="",
                stderr=f"Command timed out after {timeout}s",
                exit_code=-1,
                duration=time.monotonic() - start,
            )

        return ExecResult(
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
            exit_code=proc.returncode or 0,
            duration=time.monotonic() - start,
        )

    async def list_tools(self) -> str:
        if not self._container_id:
            if self.auto_start:
                await self.start()
            else:
                return "Sandbox not started."

        result = await self.exec(
            "which",
            "-- ls git node npm python3 aws gcloud gh docker jq yq rg fdfind curl wget "
            "make gcc go rustc java ssh tar zip unzip vim tmux",
            timeout=10,
        )

        found = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if "/" in line:
                tool_name = line.rsplit("/", 1)[-1]
                found.append(tool_name)

        if found:
            tools_list = "\n".join(f"  ✓ {t}" for t in sorted(found))
            return f"Available tools in sandbox:\n{tools_list}"
        else:
            return "Could not detect tools. Try running 'which <tool>' via run_cli."

    async def info(self) -> str:
        lines = []
        lines.append("Sandbox Status:")
        lines.append("  Type: Docker")
        lines.append(f"  Image: {self.image}")

        if self._container_id:
            result = await self._run_docker(
                [
                    "container", "inspect",
                    "--format", "{{.State.Status}}",
                    self.container_name,
                ],
                timeout=15,
            )
            status = result.stdout.strip()
            lines.append(f"  Container: {self.container_name}")
            lines.append(f"  Status: {status}")

            uptime_result = await self._run_docker(
                [
                    "container", "inspect",
                    "--format", "{{.State.StartedAt}}",
                    self.container_name,
                ],
                timeout=15,
            )
            started = uptime_result.stdout.strip()
            if started:
                lines.append(f"  Started: {started}")
        else:
            lines.append("  Container: not running")

        ws = self.workspace_cfg
        lines.append(f"  Workspace mount: {ws.get('mount', False)}")
        if ws.get("mount"):
            lines.append(f"    Host: {ws.get('host_path', '(current dir)')}")
            lines.append(f"    Container: {ws.get('container_path', '/workspace')}")
            lines.append(f"    Read-only: {ws.get('read_only', False)}")

        sec = self.config.get("security", {})
        lines.append(f"  Security mode: {sec.get('mode', 'blocklist')}")
        lines.append(f"  Max timeout: {sec.get('max_timeout', 300)}s")

        return "\n".join(lines)
