from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG: dict[str, Any] = {
    "sandbox": {
        "type": "docker",
        "image": "cli-mcp-tools:latest",
        "container_name": "cli-mcp-sandbox",
        "persistent": True,
        "auto_start": True,
        "auto_stop": False,
        "volume_mounts": [
            {
                "host_path": "/var/run/docker.sock",
                "container_path": "/var/run/docker.sock",
                "read_only": True,
            }
        ],
        "workspace": {
            "mount": True,
            "host_path": "",
            "container_path": "/workspace",
            "read_only": False,
        },
    },
    "security": {
        "mode": "blocklist",
        "blocklist": [
            {
                "pattern": "rm\\s+-rf\\s+[\\/\\\\]$",
                "reason": "Prevents recursive root deletion",
            },
            {
                "pattern": "dd\\s+if=",
                "reason": "Prevents raw disk writes",
            },
            {
                "pattern": "mkfs\\..*",
                "reason": "Prevents filesystem formatting",
            },
            {
                "pattern": ">\\s*/dev/",
                "reason": "Prevents direct device access",
            },
            {
                "pattern": "chmod\\s+777\\s+/",
                "reason": "Prevents world-writable root",
            },
            {
                "pattern": "^:\\s*\\(\\s*\\)\\s*\\{",
                "reason": "Prevents fork bombs",
            },
        ],
        "max_timeout": 300,
        "max_output_lines": 2000,
        "max_output_bytes": 1_048_576,
    },
    "tools": {
        "default_image": "cli-mcp-tools:latest",
        "command_timeout": 60,
        "env": {
            "PYTHONUNBUFFERED": "1",
            "NODE_ENV": "development",
            "CI": "true",
        },
        "tool_aliases": {
            "dc": "docker compose",
            "g": "git",
            "p": "python3",
        },
    },
    "server": {
        "transports": ["stdio"],
        "http": {
            "host": "127.0.0.1",
            "port": 8080,
            "auth_token_env": "CLI_MCP_AUTH_TOKEN",
        },
    },
}

ENV_OVERRIDES: dict[str, str] = {
    "CLI_MCP_IMAGE": "sandbox.image",
    "CLI_MCP_CONTAINER_NAME": "sandbox.container_name",
    "CLI_MCP_AUTH_TOKEN": "server.http.auth_token_env",
    "CLI_MCP_TIMEOUT": "tools.command_timeout",
    "CLI_MCP_MAX_TIMEOUT": "security.max_timeout",
    "CLI_MCP_WORKSPACE": "sandbox.workspace.host_path",
}


def _deep_set(d: dict[str, Any], keys: list[str], value: Any) -> None:
    for key in keys[:-1]:
        if key not in d:
            d[key] = {}
        d = d[key]
    d[keys[-1]] = value


def _deep_get(d: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key)
        else:
            return None
    return d


def load_config(path: str | None = None) -> dict[str, Any]:
    config = DEFAULT_CONFIG.copy()

    if path is None:
        candidates = [
            Path("cli-mcp.yaml"),
            Path("cli-mcp.yml"),
            Path.home() / ".config" / "cli-mcp" / "config.yaml",
            Path.home() / ".config" / "cli-mcp" / "config.yml",
        ]
    else:
        candidates = [Path(path)]

    loaded = False
    for candidate in candidates:
        if candidate.exists():
            with open(candidate) as f:
                overrides = yaml.safe_load(f) or {}
            _deep_merge(config, overrides)
            loaded = True
            break

    for env_key, config_path in ENV_OVERRIDES.items():
        value = os.environ.get(env_key)
        if value is not None:
            keys = config_path.split(".")
            _deep_set(config, keys, _coerce_value(value))

    return config


def _coerce_value(value: str) -> str | int | bool:
    if value.lower() in ("true", "yes", "1"):
        return True
    if value.lower() in ("false", "no", "0"):
        return False
    try:
        return int(value)
    except ValueError:
        return value


def _deep_merge(base: dict, overrides: dict) -> None:
    for key, value in overrides.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
