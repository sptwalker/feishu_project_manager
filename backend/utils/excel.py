"""Excel 读写工具（基于 openpyxl）

提供通用的 xlsx 构建与解析：
- build_xlsx：将表头 + 行数据写入内存中的 xlsx，返回字节
- parse_xlsx：解析 xlsx 字节，按首行表头返回字典列表
"""
from io import BytesIO
from typing import List, Dict, Any, Optional
from openpyxl import Workbook, load_workbook


class ExcelParseError(Exception):
    """Excel 解析错误"""
    pass


def build_xlsx(headers: List[str], rows: List[List[Any]],
               sheet_title: str = "Sheet1") -> bytes:
    """构建 xlsx 并返回字节

    Args:
        headers: 表头列名
        rows: 行数据，每行为与 headers 等长的值列表
        sheet_title: 工作表名
    """
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title
    ws.append(headers)
    for row in rows:
        ws.append(list(row))

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def parse_xlsx(data: bytes, expected_headers: Optional[List[str]] = None,
               sheet_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """解析 xlsx 字节为字典列表（首行作为表头）

    Args:
        data: xlsx 文件字节
        expected_headers: 若提供，校验这些列是否都存在
        sheet_name: 指定工作表名，默认使用活动表

    Returns:
        每行一个 dict，键为表头，值为单元格值。空行被跳过。
    """
    try:
        wb = load_workbook(BytesIO(data), read_only=True, data_only=True)
    except Exception as e:
        raise ExcelParseError(f"Failed to read xlsx: {e}")

    ws = wb[sheet_name] if sheet_name else wb.active

    rows_iter = ws.iter_rows(values_only=True)
    try:
        header_row = next(rows_iter)
    except StopIteration:
        return []

    headers = [str(h).strip() if h is not None else "" for h in header_row]

    if expected_headers:
        missing = [h for h in expected_headers if h not in headers]
        if missing:
            raise ExcelParseError(f"Missing required columns: {missing}")

    result: List[Dict[str, Any]] = []
    for row in rows_iter:
        # 跳过完全为空的行
        if row is None or all(c is None or str(c).strip() == "" for c in row):
            continue
        record = {}
        for idx, header in enumerate(headers):
            if not header:
                continue
            record[header] = row[idx] if idx < len(row) else None
        result.append(record)

    wb.close()
    return result
