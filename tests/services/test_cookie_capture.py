from quark_uploader.services.cookie_capture import format_cookie_header, is_quark_cookie_domain


def test_is_quark_cookie_domain_matches_quark_hosts():
    assert is_quark_cookie_domain(".quark.cn") is True
    assert is_quark_cookie_domain("pan.quark.cn") is True
    assert is_quark_cookie_domain("example.com") is False


def test_format_cookie_header_joins_name_value_pairs():
    header = format_cookie_header({"sid": "123", "kps": "abc"})
    assert header == "sid=123; kps=abc"
