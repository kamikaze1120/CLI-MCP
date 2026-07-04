from __future__ import annotations

import os
import platform
import re
from pathlib import Path

_WINDOWS_DRIVE_RE = re.compile(r"^([A-Za-z]):[\\/](.*)")


def is_windows() -> bool:
    return platform.system() == "Windows"


def to_container_path(
    host_path: str,
    container_workspace: str = "/workspace",
    host_workspace: str | None = None,
) -> str:
    if not is_windows():
        return host_path

    path = Path(host_path)
    if not path.is_absolute():
        return os.path.join(container_workspace, host_path)

    match = _WINDOWS_DRIVE_RE.match(str(path))
    if match:
        drive = match.group(1).lower()
        rest = match.group(2).replace("\\", "/")
        container_path = f"/host_mnt/{drive}/{rest}"
    else:
        container_path = str(path).replace("\\", "/")

    if host_workspace and container_path.startswith(
        to_container_path(str(Path(host_workspace).resolve()))
    ):
        rel = os.path.relpath(
            container_path,
            to_container_path(str(Path(host_workspace).resolve())),
        )
        container_path = os.path.join(container_workspace, rel)

    return container_path


def normalize_path(path: str) -> str:
    """Convert backslash separators to forward slashes in Windows-style paths.

    Applies on any platform when the path is clearly Windows-style (drive
    letter prefix), and to any backslash path when running on Windows.
    """
    if "\\" in path and (is_windows() or _WINDOWS_DRIVE_RE.match(path)):
        return path.replace("\\", "/")
    return path


def resolve_workspace(
    config_host_path: str, cwd_param: str | None = None
) -> tuple[str, str]:
    if config_host_path:
        host_root = config_host_path
    else:
        host_root = str(Path.cwd())

    if cwd_param:
        working_dir = os.path.join(host_root, cwd_param)
    else:
        working_dir = host_root

    return host_root, working_dir


def docker_mount_args(host_path: str, container_path: str, read_only: bool = False) -> list[str]:
    """Build 'docker run' volume arguments as an argv list (safe for paths with spaces)."""
    host = normalize_path(str(Path(host_path).resolve()))
    ro_flag = ":ro" if read_only else ""
    return ["-v", f"{host}:{container_path}{ro_flag}"]


def docker_mount_flag(host_path: str, container_path: str, read_only: bool = False) -> str:
    """String form of docker_mount_args, for display purposes only."""
    return " ".join(docker_mount_args(host_path, container_path, read_only))
