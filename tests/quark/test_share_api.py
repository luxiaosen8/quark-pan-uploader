from quark_uploader.quark.share_api import build_share_create_url, build_share_password_url


def test_build_share_create_url_points_to_share_endpoint():
    assert build_share_create_url().endswith("/1/clouddrive/share")


def test_build_share_password_url_points_to_detail_endpoint():
    assert build_share_password_url().endswith("/1/clouddrive/share/password")
