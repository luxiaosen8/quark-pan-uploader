from quark_uploader.quark.file_api import QuarkFileApi
from quark_uploader.quark.session import QuarkSession
from quark_uploader.quark.share_api import QuarkShareApi
from quark_uploader.quark.upload_api import QuarkUploadApi
from quark_uploader.quark.user_api import QuarkUserApi


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
        self.calls.append({
            "method": method,
            "url": url,
            "headers": headers,
            "params": params,
            "json": json,
            "timeout": timeout,
        })
        return DummyResponse({"code": 0, "data": {"ok": True}})


def test_quark_session_request_merges_base_params():
    http = DummyHTTP()
    session = QuarkSession(cookie="sid=123", http=http)

    payload = session.request("GET", "/example", params={"foo": "bar"})

    assert payload["code"] == 0
    assert http.calls[0]["url"].endswith("/example")
    assert http.calls[0]["params"]["pr"] == "ucpro"
    assert http.calls[0]["params"]["foo"] == "bar"


def test_user_api_get_capacity_info_uses_growth_endpoint():
    http = DummyHTTP()
    session = QuarkSession(cookie="sid=123", http=http)

    QuarkUserApi(session).get_capacity_info()

    assert http.calls[0]["method"] == "GET"
    assert http.calls[0]["url"].endswith("/1/clouddrive/capacity/growth/info")


def test_file_api_list_directory_calls_sort_endpoint():
    http = DummyHTTP()
    session = QuarkSession(cookie="sid=123", http=http)

    QuarkFileApi(session).list_directory("root-fid")

    assert http.calls[0]["method"] == "GET"
    assert http.calls[0]["url"].endswith("/1/clouddrive/file/sort")
    assert http.calls[0]["params"]["pdir_fid"] == "root-fid"


def test_file_api_create_directory_calls_file_endpoint():
    http = DummyHTTP()
    session = QuarkSession(cookie="sid=123", http=http)

    QuarkFileApi(session).create_directory("root-fid", "课程A")

    assert http.calls[0]["method"] == "POST"
    assert http.calls[0]["url"].endswith("/1/clouddrive/file")
    assert http.calls[0]["json"]["file_name"] == "课程A"


def test_upload_api_preupload_uses_post_json_payload():
    http = DummyHTTP()
    session = QuarkSession(cookie="sid=123", http=http)

    QuarkUploadApi(session).preupload({"file_name": "demo.txt"})

    assert http.calls[0]["method"] == "POST"
    assert http.calls[0]["url"].endswith("/1/clouddrive/file/upload/pre")
    assert http.calls[0]["json"]["file_name"] == "demo.txt"


def test_upload_api_update_hash_calls_update_hash_endpoint():
    http = DummyHTTP()
    session = QuarkSession(cookie="sid=123", http=http)

    QuarkUploadApi(session).update_hash({"task_id": "task-1"})

    assert http.calls[0]["method"] == "POST"
    assert http.calls[0]["url"].endswith("/1/clouddrive/file/update/hash")


def test_upload_api_get_auth_calls_upload_auth_endpoint():
    http = DummyHTTP()
    session = QuarkSession(cookie="sid=123", http=http)

    QuarkUploadApi(session).get_upload_auth({"task_id": "task-1"})

    assert http.calls[0]["method"] == "POST"
    assert http.calls[0]["url"].endswith("/1/clouddrive/file/upload/auth")


def test_share_api_create_share_uses_post_json_payload():
    http = DummyHTTP()
    session = QuarkSession(cookie="sid=123", http=http)

    QuarkShareApi(session).create_share({"title": "lesson-a"})

    assert http.calls[0]["method"] == "POST"
    assert http.calls[0]["url"].endswith("/1/clouddrive/share")
    assert http.calls[0]["json"]["title"] == "lesson-a"
