from quark_uploader.quark.task_api import QuarkTaskApi
from quark_uploader.quark.session import QuarkSession


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class DummyHTTP:
    def __init__(self):
        self.calls = []

    def request(self, method, url, headers=None, params=None, json=None, timeout=None):
        self.calls.append({"method": method, "url": url, "params": params, "json": json})
        return DummyResponse({"code": 0, "data": {"status": 2}})


def test_task_api_get_task_calls_task_endpoint():
    http = DummyHTTP()
    session = QuarkSession(cookie="sid=123", http=http)

    QuarkTaskApi(session).get_task("task-1", retry_index=2)

    assert http.calls[0]["method"] == "GET"
    assert http.calls[0]["url"].endswith("/1/clouddrive/task")
    assert http.calls[0]["params"]["task_id"] == "task-1"
    assert http.calls[0]["params"]["retry_index"] == 2
