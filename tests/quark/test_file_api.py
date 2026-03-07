from quark_uploader.quark.file_api import build_sort_params
from quark_uploader.quark.user_api import build_capacity_info_url


def test_build_sort_params_uses_expected_parent_id():
    params = build_sort_params("root-fid")
    assert params["pdir_fid"] == "root-fid"
    assert params["_fetch_sub_dirs"] == 1


def test_build_capacity_info_url_points_to_growth_info_endpoint():
    assert build_capacity_info_url().endswith("/1/clouddrive/capacity/growth/info")
