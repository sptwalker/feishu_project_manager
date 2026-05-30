import pytest
from backend.utils.excel import build_xlsx, parse_xlsx, ExcelParseError


def test_build_and_parse_roundtrip():
    headers = ["任务名称", "负责人ID", "完成度"]
    rows = [["任务A", 1, 50], ["任务B", 2, 0]]
    data = build_xlsx(headers, rows)
    parsed = parse_xlsx(data)
    assert len(parsed) == 2
    assert parsed[0]["任务名称"] == "任务A"
    assert parsed[0]["负责人ID"] == 1
    assert parsed[1]["完成度"] == 0


def test_parse_skips_empty_rows():
    data = build_xlsx(["A", "B"], [["x", "y"], [None, None], ["z", "w"]])
    parsed = parse_xlsx(data)
    assert len(parsed) == 2


def test_parse_expected_headers_ok():
    data = build_xlsx(["任务名称", "负责人ID"], [["t", 1]])
    parsed = parse_xlsx(data, expected_headers=["任务名称", "负责人ID"])
    assert len(parsed) == 1


def test_parse_missing_headers_raises():
    data = build_xlsx(["任务名称"], [["t"]])
    with pytest.raises(ExcelParseError):
        parse_xlsx(data, expected_headers=["任务名称", "负责人ID"])


def test_parse_empty_sheet_returns_empty():
    data = build_xlsx([], [])
    assert parse_xlsx(data) == []


def test_parse_invalid_bytes_raises():
    with pytest.raises(ExcelParseError):
        parse_xlsx(b"not an xlsx file")
