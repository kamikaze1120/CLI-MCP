
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
