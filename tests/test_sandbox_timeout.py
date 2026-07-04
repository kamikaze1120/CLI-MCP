import asyncio
import sys
import time

from cli_mcp.sandbox import _communicate_with_timeout


class TestTimeoutEnforcement:
    def test_long_running_process_is_killed(self):
        async def run():
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-c", "import time; time.sleep(30)",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                await _communicate_with_timeout(proc, timeout=1)
            except asyncio.TimeoutError:
                return proc
            raise AssertionError("expected TimeoutError")

        start = time.monotonic()
        proc = asyncio.run(run())
        elapsed = time.monotonic() - start

        assert elapsed < 10, f"process was not killed promptly (took {elapsed:.1f}s)"
        assert proc.returncode is not None, "process is still running"

    def test_fast_process_completes(self):
        async def run():
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-c", "print('ok')",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            return await _communicate_with_timeout(proc, timeout=10)

        stdout, _ = asyncio.run(run())
        assert stdout.strip() == b"ok"
