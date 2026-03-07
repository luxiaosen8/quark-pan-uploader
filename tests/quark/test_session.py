from quark_uploader.quark.session import QuarkSession, build_cookie_headers


def test_build_cookie_headers_includes_cookie_header():
    headers = build_cookie_headers("sid=123")
    assert headers["Cookie"] == "sid=123"
    assert headers["Accept"] == "application/json, text/plain, */*"


def test_quark_session_builds_base_query_params():
    session = QuarkSession(cookie="sid=123")
    assert session.base_params == {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
