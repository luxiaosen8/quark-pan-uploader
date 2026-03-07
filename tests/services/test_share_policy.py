from quark_uploader.services.share_policy import build_share_payload


def test_build_share_payload_uses_folder_id_and_title():
    payload = build_share_payload(fid="abc", title="lesson-a")
    assert payload["fid_list"] == ["abc"]
    assert payload["title"] == "lesson-a"
    assert payload["url_type"] == 2
