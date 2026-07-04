import asyncio

from cli_mcp.server import BearerAuthMiddleware, create_server


class RecordingApp:
    def __init__(self):
        self.called = False

    async def __call__(self, scope, receive, send):
        self.called = True


def _http_scope(headers):
    return {"type": "http", "headers": headers}


async def _noop_receive():
    return {"type": "http.request"}


class TestBearerAuthMiddleware:
    def test_rejects_missing_token(self):
        inner = RecordingApp()
        middleware = BearerAuthMiddleware(inner, "secret")
        sent = []

        async def send(message):
            sent.append(message)

        asyncio.run(middleware(_http_scope([]), _noop_receive, send))
        assert not inner.called
        assert sent[0]["status"] == 401

    def test_rejects_wrong_token(self):
        inner = RecordingApp()
        middleware = BearerAuthMiddleware(inner, "secret")
        sent = []

        async def send(message):
            sent.append(message)

        scope = _http_scope([(b"authorization", b"Bearer wrong")])
        asyncio.run(middleware(scope, _noop_receive, send))
        assert not inner.called
        assert sent[0]["status"] == 401

    def test_accepts_correct_token(self):
        inner = RecordingApp()
        middleware = BearerAuthMiddleware(inner, "secret")

        async def send(message):
            raise AssertionError("should not send a response itself")

        scope = _http_scope([(b"authorization", b"Bearer secret")])
        asyncio.run(middleware(scope, _noop_receive, send))
        assert inner.called

    def test_passes_through_non_http(self):
        inner = RecordingApp()
        middleware = BearerAuthMiddleware(inner, "secret")

        async def send(message):
            raise AssertionError("should not send a response itself")

        asyncio.run(middleware({"type": "lifespan"}, _noop_receive, send))
        assert inner.called


class TestCreateServer:
    def test_registers_expected_tools(self):
        from cli_mcp.config import load_config

        mcp = create_server(load_config("/nonexistent/cli-mcp.yaml"))
        tools = asyncio.run(mcp.list_tools())
        names = {t.name for t in tools}
        assert names == {"run_cli", "list_tools", "sandbox_info", "reset_sandbox", "run_script"}
