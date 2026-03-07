from quark_uploader.services.upload_strategy import decide_upload_mode


def test_decide_upload_mode_returns_instant_when_preupload_hits():
    mode = decide_upload_mode({"rapid_upload": True})
    assert mode == "instant"


def test_decide_upload_mode_returns_multipart_when_requested():
    mode = decide_upload_mode({"multipart": True})
    assert mode == "multipart"
