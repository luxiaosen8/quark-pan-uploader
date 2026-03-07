from quark_uploader.quark.upload_api import build_upload_finish_url, build_upload_pre_url


def test_build_upload_pre_url_points_to_preupload_endpoint():
    assert build_upload_pre_url().endswith("/1/clouddrive/file/upload/pre")


def test_build_upload_finish_url_points_to_finish_endpoint():
    assert build_upload_finish_url().endswith("/1/clouddrive/file/upload/finish")
