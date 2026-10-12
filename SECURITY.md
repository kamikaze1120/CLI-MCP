# Security guidance

CLI MCP Gateway executes commands requested by an AI assistant. Treat the assistant, its input, and generated commands as untrusted until reviewed.

## Deployment checklist

- Run the gateway and Docker daemon on hosts that are dedicated to the intended workload, not on machines with production credentials or sensitive personal files.
- Prefer the allowlist security mode and limit enabled commands to those required by your workflow. A command blocklist is defense in depth, not a security boundary.
- Mount only the workspace directories actually needed. Use read-only workspace mounts when the task does not require writes.
- **Avoid mounting the Docker socket into the sandbox.** Access to a Docker daemon can allow operations outside the intended container boundary, even when a socket mount is described as read-only.
- Do not inject cloud credentials, SSH keys, API tokens, or broad host environment variables into the sandbox unless strictly required. Use narrowly scoped, short-lived credentials.
- Apply least privilege to the host user and container, and use non-root execution where practical.
- Set command timeouts, output-size limits, and resource limits; also monitor activity and network access.
- Require human approval for commands that modify infrastructure, deploy software, delete data, or transmit secrets.
- Before exposing an HTTP transport beyond localhost, configure authentication, TLS at the ingress, access restrictions, and audit logging. Check the actual deployed settings instead of assuming defaults are safe.
- Review dependency and base-image updates regularly and test recovery procedures.

## Trust boundaries

A container reduces accidental host changes but is not a complete security boundary. Mounted directories and sockets, network access, and credentials determine what a command can reach. Shell chaining and tool-specific flags can create risks beyond a simple command-name allowlist. Review configured policies and test with a deliberately restricted account.

## Reporting a vulnerability

Avoid publicly posting exploits, tokens, or other sensitive information in an issue. Contact the repository maintainer privately to coordinate disclosure. If GitHub private vulnerability reporting is enabled for this repository, use the repository's **Security** tab.

This document is deployment guidance, not a claim that each control is implemented or enabled by default.
