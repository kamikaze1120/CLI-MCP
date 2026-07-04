from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


class SecurityError(Exception):
    pass


# Shell constructs that would let a command chain into other commands
# (defeating allowlist mode, since commands run through 'bash -c').
_SHELL_CHAINING_RE = re.compile(r"[;&|`\n]|\$\(|<\(|>\(")


@dataclass
class BlocklistEntry:
    pattern: str
    reason: str = ""
    _compiled: re.Pattern | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self._compiled = re.compile(self.pattern, re.IGNORECASE)

    def matches(self, text: str) -> bool:
        return bool(self._compiled.search(text)) if self._compiled else False


@dataclass
class SecurityConfig:
    mode: str = "blocklist"
    blocklist: list[BlocklistEntry] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    max_timeout: int = 300
    max_output_lines: int = 2000
    max_output_bytes: int = 1_048_576


class SecurityChecker:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = SecurityConfig()
        if config:
            self._load_config(config)

    def _load_config(self, config: dict[str, Any]) -> None:
        sec = config.get("security", {})
        self.config.mode = sec.get("mode", "blocklist")
        self.config.max_timeout = sec.get("max_timeout", 300)
        self.config.max_output_lines = sec.get("max_output_lines", 2000)
        self.config.max_output_bytes = sec.get("max_output_bytes", 1_048_576)

        self.config.blocklist = [
            BlocklistEntry(
                pattern=entry["pattern"],
                reason=entry.get("reason", ""),
            )
            for entry in sec.get("blocklist", [])
        ]

        self.config.allowed_tools = sec.get("allowed_tools", [])

    def validate(self, tool: str, args: str, timeout: int) -> None:
        command = f"{tool} {args}".strip()

        if self.config.mode == "allowlist":
            if self.config.allowed_tools and tool not in self.config.allowed_tools:
                raise SecurityError(
                    f"Tool '{tool}' is not in the allowed list. "
                    f"Allowed: {', '.join(self.config.allowed_tools)}"
                )
            if _SHELL_CHAINING_RE.search(args):
                raise SecurityError(
                    "Shell chaining characters (;, &, |, `, $(, <(, >() are not "
                    "permitted in allowlist mode, as they could invoke tools "
                    "outside the allowed list."
                )

        # The blocklist applies in every mode.
        for entry in self.config.blocklist:
            if entry.matches(command):
                raise SecurityError(
                    f"Command blocked by security policy: {entry.reason or 'Pattern matched'}\n"
                    f"  Pattern: {entry.pattern}\n"
                    f"  Command: {command}"
                )

        if timeout > self.config.max_timeout:
            raise SecurityError(
                f"Timeout {timeout}s exceeds maximum allowed ({self.config.max_timeout}s)"
            )

    def truncate_output(self, output: str) -> str:
        lines = output.splitlines()
        if len(lines) > self.config.max_output_lines:
            lines = lines[: self.config.max_output_lines]
            lines.append(f"... output truncated at {self.config.max_output_lines} lines")

        result = "\n".join(lines)
        if len(result.encode("utf-8")) > self.config.max_output_bytes:
            result = result[: self.config.max_output_bytes]
            result += "\n... output truncated (max bytes exceeded)"

        return result
