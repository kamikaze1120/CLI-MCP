import os
import sys
from pathlib import Path

import pytest

from cli_mcp.path_utils import (
    is_windows,
    to_container_path,
    normalize_path,
    docker_mount_flag,
)


class TestNormalizePath:
    def test_backslash_to_forward_slash(self):
        result = normalize_path("C:\\Users\\test\\project")
        assert "\\" not in result


class TestDockerMountFlag:
    def test_mount_flag_read_write(self):
        result = docker_mount_flag("/host/path", "/container/path")
        assert result.startswith("-v ")
        assert "/host/path:/container/path" in result

    def test_mount_flag_read_only(self):
        result = docker_mount_flag("/host/path", "/container/path", read_only=True)
        assert ":ro" in result
