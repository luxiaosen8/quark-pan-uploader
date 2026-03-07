from quark_uploader.services.remote_paths import split_relative_parts


def test_split_relative_parts_normalizes_nested_paths():
    assert split_relative_parts("chapter1/video/part1.mp4") == ["chapter1", "video"]
    assert split_relative_parts("part1.mp4") == []
