from pathlib import Path

from quark_uploader.services.oss_transport import RequestsOssTransport


class DummyResponse:
    def __init__(self, status_code=200, headers=None, text=""):
        self.status_code = status_code
        self.headers = headers or {"etag": '"etag-1"'}
        self.text = text


class DummyRequests:
    def __init__(self):
        self.put_calls = []
        self.post_calls = []

    def put(self, url, data=None, headers=None, timeout=None):
        self.put_calls.append((url, headers, timeout, data))
        return DummyResponse()

    def post(self, url, data=None, headers=None, timeout=None):
        self.post_calls.append((url, headers, timeout, data))
        return DummyResponse(status_code=200, headers={})


def test_requests_oss_transport_uploads_single_part_and_returns_etag(tmp_path: Path):
    file_path = tmp_path / "cover.txt"
    file_path.write_text("12", encoding="utf-8")
    client = DummyRequests()
    transport = RequestsOssTransport(http_client=client)

    result = transport.upload_single_part(file_path, "https://example.com/upload", {"authorization": "AUTH"})

    assert client.put_calls[0][0] == "https://example.com/upload"
    assert client.put_calls[0][1]["authorization"] == "AUTH"
    assert result == {"etag": "etag-1"}


def test_requests_oss_transport_uploads_part_range(tmp_path: Path):
    file_path = tmp_path / "multi.bin"
    file_path.write_bytes(b"abcdefgh")
    client = DummyRequests()
    transport = RequestsOssTransport(http_client=client)

    result = transport.upload_part(file_path, "https://example.com/upload", {"authorization": "AUTH"}, offset=2, size=3)

    assert client.put_calls[0][3] == b"cde"
    assert result == {"etag": "etag-1"}


def test_requests_oss_transport_completes_multipart_upload():
    client = DummyRequests()
    transport = RequestsOssTransport(http_client=client)

    result = transport.complete_multipart_upload("https://example.com/complete", {"authorization": "AUTH"}, "<xml />")

    assert client.post_calls[0][0] == "https://example.com/complete"
    assert client.post_calls[0][1]["authorization"] == "AUTH"
    assert client.post_calls[0][3] == "<xml />"
    assert result == {"ok": True}
