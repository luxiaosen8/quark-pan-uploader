from pathlib import Path

from quark_uploader.services.oss_transport import RequestsOssTransport


class DummyResponse:
    def __init__(self, status_code=200, headers=None, text=""):
        self.status_code = status_code
        self.headers = headers or {"etag": '"etag-1"'}
        self.text = text


class DummyRequests:
    def __init__(self):
        self.calls = []

    def put(self, url, data=None, headers=None, timeout=None):
        self.calls.append((url, headers, timeout, data))
        return DummyResponse()


def test_requests_oss_transport_uploads_single_part_and_returns_etag(tmp_path: Path):
    file_path = tmp_path / "cover.txt"
    file_path.write_text("12", encoding="utf-8")
    client = DummyRequests()
    transport = RequestsOssTransport(http_client=client)

    result = transport.upload_single_part(file_path, "https://example.com/upload", {"authorization": "AUTH"})

    assert client.calls[0][0] == "https://example.com/upload"
    assert client.calls[0][1]["authorization"] == "AUTH"
    assert result == {"etag": "etag-1"}
