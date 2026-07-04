import os
import tempfile

import yaml

from cli_mcp.config import DEFAULT_CONFIG, _deep_merge, load_config


class TestConfigLoading:
    def test_default_config(self):
        config = load_config()
        assert config["sandbox"]["type"] == "docker"
        assert config["sandbox"]["image"] == "cli-mcp-tools:latest"
        assert config["security"]["mode"] == "blocklist"
        assert config["server"]["transports"] == ["stdio"]

    def test_load_from_file(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump({"sandbox": {"image": "my-custom-image:1.0"}}, f)
            f.flush()
            config = load_config(f.name)

        os.unlink(f.name)
        assert config["sandbox"]["image"] == "my-custom-image:1.0"
        assert config["sandbox"]["type"] == "docker"

    def test_deep_merge_replaces_nested(self):
        base = {
            "a": {"b": 1, "c": 2},
            "d": 3,
        }
        override = {
            "a": {"b": 99},
            "e": 4,
        }
        _deep_merge(base, override)
        assert base["a"]["b"] == 99
        assert base["a"]["c"] == 2
        assert base["d"] == 3
        assert base["e"] == 4

    def test_empty_config_uses_defaults(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump({}, f)
            f.flush()
            config = load_config(f.name)

        os.unlink(f.name)
        assert config["sandbox"]["type"] == "docker"


class TestDefaultsIsolation:
    def test_load_config_does_not_mutate_defaults(self):
        original_image = DEFAULT_CONFIG["sandbox"]["image"]
        config = load_config("/nonexistent/cli-mcp.yaml")
        config["sandbox"]["image"] = "mutated:latest"
        config["security"]["blocklist"].clear()

        assert DEFAULT_CONFIG["sandbox"]["image"] == original_image
        assert len(DEFAULT_CONFIG["security"]["blocklist"]) > 0
