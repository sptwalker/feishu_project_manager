from backend.utils import feishu_cards


def test_build_notification_card_structure():
    card = feishu_cards.build_notification_card("标题", ["行1", "行2"])
    assert card["header"]["title"]["content"] == "标题"
    assert card["header"]["template"] == feishu_cards.HEADER_BLUE
    content = card["elements"][0]["text"]["content"]
    assert "行1" in content and "行2" in content


def test_build_notification_card_empty_lines():
    card = feishu_cards.build_notification_card("T", [])
    # 空正文不应报错，content 至少为占位空白
    assert card["elements"][0]["text"]["content"] == " "


def test_task_status_card():
    card = feishu_cards.build_task_status_card("任务A", "pending", "completed", "张三", "项目X")
    assert "任务A" in card["header"]["title"]["content"]
    content = card["elements"][0]["text"]["content"]
    assert "pending" in content and "completed" in content
    assert "张三" in content
    assert "项目X" in content


def test_risk_card_resolved_is_green():
    card = feishu_cards.build_risk_card("风险A", "open", "resolved")
    assert card["header"]["template"] == feishu_cards.HEADER_GREEN


def test_risk_card_non_resolved_is_orange():
    card = feishu_cards.build_risk_card("风险A", "open", "monitoring")
    assert card["header"]["template"] == feishu_cards.HEADER_ORANGE


def test_project_card():
    card = feishu_cards.build_project_card("项目Y", "in_progress", 80, "李四")
    content = card["elements"][0]["text"]["content"]
    assert "80%" in content
    assert "李四" in content
