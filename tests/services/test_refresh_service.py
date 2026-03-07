from quark_uploader.services.refresh_service import DriveRefreshService, extract_account_summary, extract_folder_nodes


class FakeUserApi:
    def get_capacity_info(self):
        return {
            "data": {
                "member": {"nickname": "测试用户"},
                "capacity": {"total": 1000, "used": 400},
            }
        }


class FakeFileApi:
    def __init__(self):
        self.calls = []

    def list_directory(self, parent_fid: str):
        self.calls.append(parent_fid)
        return {
            "data": {
                "list": [
                    {"fid": "folder-1", "file_name": "资料", "dir": True, "file_count": 3},
                    {"fid": "file-1", "file_name": "ignore.txt", "dir": False},
                ]
            }
        }


def test_extract_account_summary_reads_capacity_payload():
    summary = extract_account_summary({
        "data": {
            "member": {"nickname": "测试用户"},
            "capacity": {"total": 1000, "used": 400},
        }
    })

    assert summary.nickname == "测试用户"
    assert summary.total_bytes == 1000
    assert summary.available_bytes == 600


def test_extract_folder_nodes_only_keeps_directories():
    nodes = extract_folder_nodes("0", {
        "data": {
            "list": [
                {"fid": "folder-1", "file_name": "资料", "dir": True, "file_count": 3},
                {"fid": "file-1", "file_name": "ignore.txt", "dir": False},
            ]
        }
    })

    assert len(nodes) == 1
    assert nodes[0].fid == "folder-1"
    assert nodes[0].name == "资料"


def test_drive_refresh_service_loads_account_and_root_nodes():
    user_api = FakeUserApi()
    file_api = FakeFileApi()
    service = DriveRefreshService(user_api=user_api, file_api=file_api)

    result = service.refresh()

    assert result.account.nickname == "测试用户"
    assert [node.fid for node in result.root_nodes] == ["folder-1"]
    assert file_api.calls == ["0"]
