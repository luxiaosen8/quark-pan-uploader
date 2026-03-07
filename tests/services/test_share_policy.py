from quark_uploader.services.share_policy import build_share_payload


def test_build_share_payload_uses_public_link_for_passwordless_share():
    payload = build_share_payload(fid="abc", title="lesson-a")
    assert payload["fid_list"] == ["abc"]
    assert payload["title"] == "lesson-a"
    assert payload["url_type"] == 1
    assert payload["expired_type"] == 1
