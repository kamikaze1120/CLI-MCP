from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import load_config
from .server import create_server, run_http

logger = logging.getLogger("cli-mcp")


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s [%(name)s] %(message)s",
        stream=sys.stderr,
    )


def find_dockerfile() -> Path | None:
    candidates = [
        Path.cwd() / "Dockerfile",
        Path(__file__).resolve().parents[2] / "Dockerfile",  # repo root (editable install)
        Path(__file__).resolve().parent / "Dockerfile",  # packaged copy, if any
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def build_image() -> None:
    import subprocess

    dockerfile = find_dockerfile()
    if dockerfile is None:
        print("Error: Dockerfile not found.")
        print("Run this command from a clone of the cli-mcp repository, or pull a")
        print("pre-built image and set 'sandbox.image' in cli-mcp.yaml instead.")
        sys.exit(1)

    print("Building cli-mcp-tools:latest Docker image...")
    print(f"  Context: {dockerfile.parent}")
    print("  This may take 5-15 minutes depending on your network.\n")

    result = subprocess.run(
        ["docker", "build", "-t", "cli-mcp-tools:latest", "-f", str(dockerfile), "."],
        cwd=dockerfile.parent,
    )

    if result.returncode == 0:
        print("\n✓ Image built successfully: cli-mcp-tools:latest")
        print("  Run 'docker images cli-mcp-tools' to verify.")
    else:
        print(f"\n✗ Build failed with exit code {result.returncode}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CLI MCP Gateway - sandboxed CLI execution for AI assistants",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default=None,
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="HTTP host (default: 127.0.0.1, only for http transport)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="HTTP port (default: 8080, only for http transport)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to config file (default: cli-mcp.yaml in CWD)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--build-image",
        action="store_true",
        help="Build the Docker tools image and exit",
    )

    args = parser.parse_args()

    if args.build_image:
        build_image()
        return

    setup_logging(args.verbose)

    config = load_config(args.config)

    if args.transport:
        config["server"]["transports"] = [args.transport]
    if args.host:
        config["server"]["http"]["host"] = args.host
    if args.port:
        config["server"]["http"]["port"] = args.port

    mcp = create_server(config)

    transports = config["server"]["transports"]

    if "http" in transports:
        http_cfg = config["server"]["http"]
        logger.info(f"Starting HTTP server on {http_cfg['host']}:{http_cfg['port']}...")
        run_http(mcp, config)
    else:
        logger.info("Starting stdio server...")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
