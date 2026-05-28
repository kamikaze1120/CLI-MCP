# 🛡️ CLI MCP Gateway

**Run any CLI command through AI assistants — safely sandboxed in Docker.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)
[![Docker](https://img.shields.io/badge/docker-required-2496ED?logo=docker)](https://docker.com)

CLI MCP Gateway is a [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that gives AI assistants like Claude Desktop, Claude Code, and Cursor the ability to execute any CLI tool inside an isolated Docker container.

**No more context copying. No more switching terminals. Just ask.**

---

## ✨ Features

- **🧰 Universal CLI access** — git, npm, python, aws, gcloud, gh, docker, curl, jq, ripgrep, and 50+ tools pre-installed
- **🔒 Sandboxed by default** — every command runs inside a disposable Docker container with configurable security policies
- **⚡ Persistent container** — near-instant execution with state preserved across commands
- **🛡️ Built-in security** — configurable blocklist/allowlist, timeout enforcement, output truncation
- **🖥️ Cross-platform** — works on macOS, Linux, and Windows (Docker Desktop + WSL2)
- **🌐 Dual transport** — stdio for local development, HTTP for remote/team deployment
- **🔧 Fully configurable** — YAML config file with environment variable overrides
- **📦 Pre-built Docker image** — all tools included, ready to pull or build

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│  MCP Host (Claude Desktop / Claude Code / Cursor)       │
│    (stdio for local, HTTP for remote)                    │
└──────────────────────┬──────────────────────────────────┘
                       │ JSON-RPC 2.0
┌──────────────────────▼──────────────────────────────────┐
│              CLI MCP Gateway (Python FastMCP)             │
│                                                           │
│  Tools:  run_cli()  list_tools()  sandbox_info()          │
│          reset_sandbox()  run_script()                     │
│                                                           │
│  Config: cli-mcp.yaml  |  ENV vars                        │
└──────────────────────┬──────────────────────────────────┘
                       │ docker exec
┌──────────────────────▼──────────────────────────────────┐
│  Persistent Docker Container (cli-mcp-sandbox)            │
│  ┌────────────────────────────────────────────────────┐  │
│  │  cli-mcp-tools:latest                               │  │
│  │  • git, node/npm, python3, go, rust, java          │  │
│  │  • aws-cli, gcloud, gh, docker-cli                 │  │
│  │  • curl, jq, ripgrep, fd, yq, tmux, vim...        │  │
│  │  • workspace: /workspace ↔ host CWD               │  │
│  │  • Docker socket mounted for docker-in-docker      │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** — [Install Python](https://www.python.org/downloads/)
- **Docker** — [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS/Windows) or `docker` CLI (Linux)
- **pip** (comes with Python) or **uv** (`pip install uv`)

### 1. Install

```bash
# Clone the repo
git clone https://github.com/yourusername/cli-mcp.git
cd cli-mcp

# Install with pip
pip install .

# Or install in editable mode for development
pip install -e .
```

### 2. Build the Docker image

```bash
# Build the tools image (5-15 minutes)
cli-mcp --build-image

# Verify
docker images cli-mcp-tools
```

### 3. Start the server

```bash
# Default mode: stdio (for Claude Desktop / Claude Code)
cli-mcp

# Or with verbose logging
cli-mcp -v
```

### 4. Connect your AI assistant

<details>
<summary><b>Claude Desktop</b></summary>

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cli-mcp": {
      "command": "cli-mcp",
      "args": []
    }
  }
}
```
</details>

<details>
<summary><b>Claude Code</b></summary>

```bash
claude mcp add cli-mcp -- cli-mcp
```
</details>

<details>
<summary><b>Cursor</b></summary>

Add to Cursor settings → MCP Servers:

| Field | Value |
|---|---|
| Name | `cli-mcp` |
| Type | `command` |
| Command | `cli-mcp` |
</details>

---

## 🔧 Configuration

CLI MCP Gateway is configured via a YAML file. It looks for these files in order:

1. `./cli-mcp.yaml` (project-local)
2. `./cli-mcp.yml`
3. `~/.config/cli-mcp/config.yaml`
4. `~/.config/cli-mcp/config.yml`

### Minimal config

```yaml
# cli-mcp.yaml
sandbox:
  image: cli-mcp-tools:latest
  workspace:
    host_path: /home/user/projects
```

### Full configuration reference

See [cli-mcp.example.yaml](cli-mcp.example.yaml) for the complete configuration with all options documented.

### Environment variable overrides

| Variable | Config Path | Example |
|---|---|---|
| `CLI_MCP_IMAGE` | `sandbox.image` | `CLI_MCP_IMAGE=ghcr.io/myorg/cli-mcp-tools:v2` |
| `CLI_MCP_CONTAINER_NAME` | `sandbox.container_name` | `CLI_MCP_CONTAINER_NAME=my-sandbox` |
| `CLI_MCP_AUTH_TOKEN` | `server.http.auth_token_env` | `CLI_MCP_AUTH_TOKEN=sk-abc123...` |
| `CLI_MCP_TIMEOUT` | `tools.command_timeout` | `CLI_MCP_TIMEOUT=120` |
| `CLI_MCP_MAX_TIMEOUT` | `security.max_timeout` | `CLI_MCP_MAX_TIMEOUT=600` |
| `CLI_MCP_WORKSPACE` | `sandbox.workspace.host_path` | `CLI_MCP_WORKSPACE=/home/user/projects` |

---

## 🛠️ Tools Reference

### `run_cli`

Execute any CLI command inside the sandboxed Docker container.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `tool` | `string` | — | CLI command to run (git, npm, python3, aws, gh, etc.) |
| `args` | `string` | `""` | Space-separated arguments and flags |
| `cwd` | `string` | `"."` | Working directory relative to workspace mount |
| `timeout` | `integer` | `60` | Max execution time in seconds (max: 300) |

**Examples:**

Ask your AI assistant:
> "Show me the last 5 git commits"
> "Run npm test in the current project"
> "Check AWS S3 buckets"
> "Format this Python file with black"

### `list_tools`

List all CLI tools available in the sandbox container.

### `sandbox_info`

Show the current sandbox configuration and container status (image, uptime, workspace mount, security mode).

### `reset_sandbox`

Destroy and recreate the sandbox container. Use this to get a clean environment.

### `run_script`

Execute a short script inline without creating a file.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `language` | `string` | — | `python`, `node`, `bash`, or `sh` |
| `code` | `string` | — | The script content to execute |
| `cwd` | `string` | `"."` | Working directory |
| `timeout` | `integer` | `60` | Max execution time |

---

## 🛡️ Security

CLI MCP Gateway runs every command inside an isolated Docker container, providing strong isolation from your host system.

### Security layers

1. **Docker containerization** — commands run in an ephemeral container with no host access (except mounted volumes)
2. **Command blocklist** — regex patterns that block dangerous commands (configurable)
3. **Timeout enforcement** — commands are killed after the configured timeout
4. **Output limits** — prevents runaway output from flooding the AI context
5. **Allowlist mode** — restrict to specific tools only (for production/team deployments)

### Built-in blocklist

The following patterns are blocked by default:

| Pattern | Reason |
|---|---|
| `rm -rf /` | Prevents recursive root deletion |
| `dd if=` | Prevents raw disk writes |
| `mkfs.*` | Prevents filesystem formatting |
| `> /dev/` | Prevents direct device access |
| `chmod 777 /` | Prevents world-writable root |
| Fork bombs | Prevents denial-of-service |

### Customizing security

```yaml
security:
  mode: blocklist           # or "allowlist"
  blocklist:
    - pattern: "my-dangerous-command"
      reason: "Protects production data"
  allowed_tools:            # used only in allowlist mode
    - git
    - npm
    - python3
```

### Docker socket security

By default, the Docker socket is mounted read-only, allowing `docker` commands inside the sandbox. This enables docker-in-docker workflows. Remove the mount if you don't need it:

```yaml
sandbox:
  volume_mounts: []  # removes Docker socket mount
```

For additional security in production:
- Set `sandbox.workspace.read_only: true`
- Use allowlist mode instead of blocklist
- Run with a non-root user inside the container

---

## 🌐 Remote Deployment

CLI MCP Gateway can run as an HTTP server for team access or integration with remote workflows.

### Start with HTTP

```bash
# Start with HTTP transport
cli-mcp --transport http --host 0.0.0.0 --port 8080

# Set auth token (recommended)
export CLI_MCP_AUTH_TOKEN=$(openssl rand -hex 32)
cli-mcp --transport http
```

### Docker deployment

```bash
# Run the MCP server itself in Docker
docker run -d \
  --name cli-mcp-server \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -p 8080:8080 \
  cli-mcp-tools:latest \
  cli-mcp --transport http --host 0.0.0.0
```

### Production considerations

- 🔐 **Always set an auth token** for HTTP mode
- 🔒 Use HTTPS behind a reverse proxy (nginx, Caddy, or Cloudflare Tunnel)
- 📊 Add rate limiting at the reverse proxy level
- 🔄 Use `--security mode: allowlist` for team deployments
- 📝 Set up logging to a file with `--verbose`

---

## 💡 Use Cases

### Development assistant
Let Claude run git commands, install npm packages, run tests, and format code — all through natural language.

### DevOps / Cloud operations
Query AWS resources, deploy with gcloud, manage Docker containers, and run kubectl commands without leaving the chat.

### Scripting & automation
Generate and execute Python scripts, bash one-liners, or Node.js snippets in seconds.

### CI/CD debugging
Debug pipeline issues by running the same commands your CI runner would execute — in an equivalent environment.

### Learning & experimentation
Try out CLI tools, test commands, and explore APIs in a safe, isolated environment before using them in production.

---

## ❓ FAQ

### Why Docker instead of running commands directly?

Docker provides strong isolation, a consistent environment across platforms, and prevents accidental damage to the host system. It also means the available tools are the same regardless of what's installed on the host.

### Can I use my own Docker image?

Yes. Set `sandbox.image` in the config or `CLI_MCP_IMAGE` environment variable to any Docker image. It just needs the tools you want to use and `sleep infinity` (or similar) as the default command.

### Is this free?

Yes, it's MIT-licensed open source. The only costs are Docker Desktop (free for personal use) and optionally a VPS (~$5-10/month) if you want remote HTTP access.

### Does it work on Windows?

Yes. Docker Desktop on Windows with WSL2 backend is fully supported. The path translation layer handles Windows paths automatically.

### How do I update the tools?

Rebuild the image: `cli-mcp --build-image` and reset the sandbox: `reset_sandbox()`. Or pull an updated version: `docker pull ghcr.io/yourusername/cli-mcp-tools:latest` → `reset_sandbox()`.

---

## 📦 Project Structure

```
cli-mcp/
├── src/
│   ├── main.py          # CLI entrypoint with argparse
│   ├── server.py        # FastMCP server & tool definitions
│   ├── sandbox.py       # Docker container lifecycle manager
│   ├── security.py      # Blocklist/allowlist & output limits
│   ├── config.py        # YAML config loader with env overrides
│   └── path_utils.py    # Cross-platform path translation
├── tests/               # pytest test suite
├── Dockerfile           # Pre-built tools image (Ubuntu 24.04)
├── cli-mcp.example.yaml # Documented configuration reference
└── pyproject.toml       # Python package metadata
```

---

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Run tests: `pytest`
5. Submit a pull request

Please ensure your code passes linting (`ruff check`) and all tests.

---

## 📄 License

[MIT](LICENSE) — Free to use, modify, and distribute. Commercial use is permitted.

---

<div align="center">
  <strong>Built with ❤️ for the AI developer community</strong>
  <br>
  <a href="https://modelcontextprotocol.io">Model Context Protocol</a>
</div>
