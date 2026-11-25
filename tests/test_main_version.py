"""Version reporting must exit before loading config or starting the server."""

from importlib.metadata import PackageNotFoundError, version
from unittest.mock import patch

import pytest

from cli_mcp.main import main


def test_version_uses_installed_distribution_and_does_not_start(capsys):
    with (
        patch("sys.argv", ["cli-mcp", "--version"]),
        patch("cli_mcp.main.load_config") as config,
        patch("cli_mcp.main.create_server") as server,
    ):
        with pytest.raises(SystemExit) as error:
            main()
    assert error.value.code == 0
    assert capsys.readouterr().out == f"cli-mcp {version('cli-mcp')}\n"
    config.assert_not_called()
    server.assert_not_called()


@pytest.mark.parametrize("flag", ["--version", "--help"])
def test_missing_metadata_keeps_parser_usable(flag, capsys):
    with (
        patch("sys.argv", ["cli-mcp", flag]),
        patch("cli_mcp.main.version", side_effect=PackageNotFoundError("cli-mcp")),
        patch("cli_mcp.main.load_config") as config,
    ):
        with pytest.raises(SystemExit) as error:
            main()
    assert error.value.code == 0
    output = capsys.readouterr().out
    if flag == "--version":
        assert output == "cli-mcp unknown\n"
    else:
        assert "--version" in output
    config.assert_not_called()
