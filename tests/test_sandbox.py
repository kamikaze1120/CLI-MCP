
import asyncio
import subprocess
from unittest.mock import AsyncMock

import pytest

from cli_mcp.sandbox import DockerSandbox


class TestDockerSandbox:
    def test_init(self):
        config = {
            "sandbox": {
                "image": "cli-mcp-tools:latest",
                "container_name": "test-sandbox",
                "persistent": True,
                "auto_start": True,
                "auto_stop": False,
                "volume_mounts": [],
                "workspace": {
                    "mount": False,
                    "host_path": "",
                    "container_path": "/workspace",
                    "read_only": False,
                },
            },
            "tools": {
                "env": {},
                "tool_aliases": {},
            },
            "security": {},
        }
        sandbox = DockerSandbox(config)
        assert sandbox.image == "cli-mcp-tools:latest"
        assert sandbox.container_name == "test-sandbox"
        assert sandbox.persistent is True

    def test_build_volume_flags_empty(self):
        config = {
            "sandbox": {
                "image": "test:latest",
                "container_name": "test",
                "persistent": True,
                "auto_start": True,
                "auto_stop": False,
                "volume_mounts": [],
                "workspace": {
                    "mount": False,
                    "host_path": "",
                    "container_path": "/workspace",
                    "read_only": False,
                },
            },
            "tools": {"env": {}, "tool_aliases": {}},
            "security": {},
        }
        sandbox = DockerSandbox(config)
        flags = sandbox._build_volume_flags()
        assert flags == []


@pytest.mark.parametrize(
    ("sandbox_settings", "expected_flags"),
    [
        ({}, []),
        ({"resources": None}, []),
        (
            {"resources": {"cpus": None, "memory": None, "pids_limit": None}},
            [],
        ),
        (
            {"resources": {"cpus": "2", "memory": "2g", "pids_limit": 512}},
            ["--cpus", "2", "--memory", "2g", "--pids-limit", "512"],
        ),
        (
            {"resources": {"memory": "512m"}},
            ["--memory", "512m"],
        ),
    ],
)
def test_start_resource_limits(sandbox_settings, expected_flags):
    config = {
        "sandbox": {
            "image": "test:latest",
            "container_name": "test",
            "workspace": {"mount": False},
            **sandbox_settings,
        },
    }
    sandbox = DockerSandbox(config)
    sandbox.ensure_image = AsyncMock()
    sandbox._run_docker = AsyncMock(
        side_effect=[
            subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="No such container"
            ),
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="container-id", stderr=""
            ),
        ]
    )

    asyncio.run(sandbox.start())

    sandbox._run_docker.assert_awaited_with(
        [
            "run", "-d", "--name", "test",
            *expected_flags,
            "test:latest", "sleep", "infinity",
        ],
        timeout=60,
    )
