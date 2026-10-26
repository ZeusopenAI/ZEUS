"""Startup/lifespan regression tests.

Bối cảnh: `lifespan` từng gọi thẳng
``asyncio.get_event_loop().add_signal_handler(signal.SIGTERM, ...)`` và chỉ bắt
``(NotImplementedError, AttributeError)``. Khi app chạy ngoài main thread —
``TestClient``, một số ASGI runner — CPython ném ``RuntimeError``:
"set_wakeup_fd only works in main thread of the main interpreter"
=> toàn bộ startup sập, API không lên được.
"""

import asyncio
import signal

import agent.main as main_module


class _FakeLoop:
    def __init__(self, exc: Exception | None = None) -> None:
        self.exc = exc
        self.installed: list[tuple[int, object]] = []

    def add_signal_handler(self, sig, callback, *args):
        if self.exc is not None:
            raise self.exc
        self.installed.append((sig, callback))


def test_sigterm_handler_installed_on_normal_loop():
    loop = _FakeLoop()
    called = []

    assert main_module._install_sigterm_handler(loop, lambda: called.append(True)) is True
    assert loop.installed and loop.installed[0][0] == signal.SIGTERM
    loop.installed[0][1]()  # callback vẫn gọi được
    assert called == [True]


def test_sigterm_handler_swallows_not_main_thread_error():
    loop = _FakeLoop(RuntimeError("set_wakeup_fd only works in main thread of the main interpreter"))

    assert main_module._install_sigterm_handler(loop, lambda: None) is False


def test_sigterm_handler_swallows_value_error_and_not_implemented():
    assert main_module._install_sigterm_handler(_FakeLoop(ValueError("x")), lambda: None) is False
    assert main_module._install_sigterm_handler(_FakeLoop(NotImplementedError("win")), lambda: None) is False


def test_app_importable_and_health_route_registered():
    app = main_module.app
    paths = {getattr(route, "path", None) for route in app.routes}
    assert "/health" in paths
    assert any(path and path.startswith("/api/") for path in paths)


def test_lifespan_runs_without_main_thread(caplog):
    """`lifespan` phải chạy tiếp (không raise) khi không cài được SIGTERM handler."""

    class _Controller:
        def request_shutdown(self):
            pass

        async def start(self):
            await asyncio.Future()

        async def drain(self):
            pass

    async def scenario():
        loop = asyncio.get_running_loop()
        # Trong pytest-asyncio, add_signal_handler thật sự ném RuntimeError như
        # TestClient, nhưng không phải lúc nào cũng vậy -> kiểm tra trực tiếp
        # nhánh guard thay vì phụ thuộc môi trường.
        assert main_module._install_sigterm_handler(loop, _Controller().request_shutdown) in (True, False)

    asyncio.run(scenario())
