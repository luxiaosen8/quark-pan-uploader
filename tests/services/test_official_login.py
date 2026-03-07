from quark_uploader.services.official_login import (
    OFFICIAL_LOGIN_PAGE_URL,
    OFFICIAL_MOBILE_LOGIN_URL,
    build_official_scan_url,
)


def test_official_login_urls_point_to_quark_hosts():
    assert OFFICIAL_LOGIN_PAGE_URL == "https://pan.quark.cn/"
    assert "client_id=532" in OFFICIAL_MOBILE_LOGIN_URL


def test_build_official_scan_url_includes_required_query_params():
    url = build_official_scan_url("token-demo")
    assert url.startswith("https://su.quark.cn/4_eMHBJ?")
    assert "token=token-demo" in url
    assert "client_id=532" in url
    assert "ssb=weblogin" in url
