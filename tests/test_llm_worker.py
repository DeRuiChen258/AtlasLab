import os

from math_agent.llm_worker import _worker_main
from math_agent.llm_worker import _normalize_proxy_env


class _ClosingConnection:
    def __init__(self):
        self.messages = []
        self._requests = [
            {
                "type": "req",
                "payload": {
                    "model": "test",
                    "messages": [{"role": "user", "content": "x"}],
                },
            }
        ]

    def send(self, payload):
        if payload.get("type") == "ready":
            self.messages.append(payload)
            return
        raise BrokenPipeError("parent closed")

    def recv(self):
        return self._requests.pop(0)


def test_worker_exits_quietly_when_parent_closes_pipe(monkeypatch):
    monkeypatch.setattr(
        "math_agent.llm_worker.litellm.completion",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("provider failed")),
    )
    connection = _ClosingConnection()
    _worker_main(connection)
    assert connection.messages == [{"type": "ready"}]


def test_normalize_proxy_env_converts_socks_to_http(monkeypatch):
    monkeypatch.setenv("ALL_PROXY", "socks://127.0.0.1:7897")
    monkeypatch.setenv("all_proxy", "socks://127.0.0.1:7897")
    _normalize_proxy_env()
    assert os.environ["ALL_PROXY"] == "http://127.0.0.1:7897"
    assert os.environ["all_proxy"] == "http://127.0.0.1:7897"
