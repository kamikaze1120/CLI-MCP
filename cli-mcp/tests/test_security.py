from cli_mcp.security import BlocklistEntry, SecurityChecker, SecurityError


class TestBlocklistEntry:
    def test_simple_pattern_match(self):
        entry = BlocklistEntry(pattern="rm\\s+-rf\\s+/", reason="test")
        assert entry.matches("rm -rf /")
        assert entry.matches("rm   -rf   /")
        assert not entry.matches("rm -rf ./tmp")

    def test_dd_pattern(self):
        entry = BlocklistEntry(pattern="dd\\s+if=")
        assert entry.matches("dd if=/dev/sda")
        assert not entry.matches("dd --help")

    def test_fork_bomb_pattern(self):
        entry = BlocklistEntry(pattern="^:\\s*\\(\\s*\\)\\s*\\{")
        assert entry.matches(":(){ :|:& };:")
        assert entry.matches(":() { :|:& };:")
        assert not entry.matches("echo hello")


class TestSecurityChecker:
    def test_blocklist_blocks_matching_command(self):
        checker = SecurityChecker({
            "security": {
                "blocklist": [
                    {"pattern": "rm\\s+-rf\\s+[\\/\\\\]$", "reason": "test"}
                ]
            }
        })
        try:
            checker.validate("rm", "-rf /", 60)
            assert False, "Should have raised SecurityError"
        except SecurityError:
            pass

    def test_allowlist_allows_only_specified(self):
        checker = SecurityChecker({
            "security": {
                "mode": "allowlist",
                "allowed_tools": ["git", "npm"],
            }
        })
        try:
            checker.validate("rm", "file.txt", 60)
            assert False, "Should have raised SecurityError"
        except SecurityError:
            pass

        checker.validate("git", "status", 60)

    def test_timeout_limit(self):
        checker = SecurityChecker({
            "security": {"max_timeout": 30}
        })
        try:
            checker.validate("git", "status", 60)
            assert False, "Should have raised SecurityError"
        except SecurityError as e:
            assert "timeout" in str(e).lower()

    def test_timeout_within_limit(self):
        checker = SecurityChecker({
            "security": {"max_timeout": 30}
        })
        checker.validate("git", "status", 30)

    def test_truncate_lines(self):
        checker = SecurityChecker({
            "security": {"max_output_lines": 3}
        })
        output = "line1\nline2\nline3\nline4\nline5"
        truncated = checker.truncate_output(output)
        lines = truncated.splitlines()
        assert len(lines) == 4
        assert "truncated" in lines[-1]

    def test_truncate_bytes(self):
        checker = SecurityChecker({
            "security": {"max_output_bytes": 20}
        })
        output = "a" * 100
        truncated = checker.truncate_output(output)
        assert len(truncated) < len(output)
        assert "truncated" in truncated
