from quark_uploader.quark.upload_api import (
    build_hash_update_payload,
    build_put_auth_meta,
    build_upload_auth_payload,
    build_upload_finish_payload,
    build_upload_finish_url,
    build_upload_pre_payload,
    build_upload_pre_url,
    parse_upload_auth_result,
)


def test_build_upload_pre_url_points_to_preupload_endpoint():
    assert build_upload_pre_url().endswith("/1/clouddrive/file/upload/pre")


def test_build_upload_finish_url_points_to_finish_endpoint():
    assert build_upload_finish_url().endswith("/1/clouddrive/file/upload/finish")


def test_build_upload_pre_payload_contains_expected_fields():
    payload = build_upload_pre_payload(
        file_name="cover.txt",
        file_size=2,
        parent_fid="root-fid",
        mime_type="text/plain",
        current_time_ms=100,
    )
    assert payload["pdir_fid"] == "root-fid"
    assert payload["file_name"] == "cover.txt"
    assert payload["size"] == 2
    assert payload["ccp_hash_update"] is True


def test_build_hash_update_payload_contains_task_and_hashes():
    payload = build_hash_update_payload(task_id="task-1", md5="m", sha1="s")
    assert payload == {"task_id": "task-1", "md5": "m", "sha1": "s"}


def test_build_upload_auth_payload_contains_task_and_meta():
    payload = build_upload_auth_payload(task_id="task-1", auth_info="info", auth_meta="meta")
    assert payload == {"task_id": "task-1", "auth_info": "info", "auth_meta": "meta"}


def test_build_upload_finish_payload_contains_task_id_and_obj_key():
    payload = build_upload_finish_payload(task_id="task-1", obj_key="obj")
    assert payload == {"task_id": "task-1", "obj_key": "obj"}


def test_build_put_auth_meta_contains_put_signature_material():
    auth_meta = build_put_auth_meta(
        mime_type="text/plain",
        oss_date="Mon, 01 Jan 2024 00:00:00 GMT",
        bucket="ul-zb",
        obj_key="obj-key",
        upload_id="upload-1",
        part_number=1,
        user_agent="aliyun-sdk-js/1.0.0",
    )
    assert auth_meta.startswith("PUT\n\ntext/plain\nMon, 01 Jan 2024 00:00:00 GMT")
    assert "/ul-zb/obj-key?partNumber=1&uploadId=upload-1" in auth_meta


def test_parse_upload_auth_result_builds_oss_upload_target():
    parsed = parse_upload_auth_result(
        auth_result={"data": {"auth_key": "AUTH"}},
        bucket="ul-zb",
        obj_key="obj-key",
        upload_id="upload-1",
        mime_type="text/plain",
        oss_date="Mon, 01 Jan 2024 00:00:00 GMT",
        user_agent="aliyun-sdk-js/1.0.0",
    )
    assert parsed["upload_url"] == "https://ul-zb.pds.quark.cn/obj-key?partNumber=1&uploadId=upload-1"
    assert parsed["headers"]["authorization"] == "AUTH"
