"""飞书交互式卡片构建工具

提供面向项目/任务/风险通知的卡片 JSON 构建函数，返回的字典可直接
作为 interactive 消息的 content 发送。
"""
from typing import Dict, Any, List

# 卡片头部颜色模板（飞书内置）
HEADER_BLUE = "blue"
HEADER_GREEN = "green"
HEADER_ORANGE = "orange"
HEADER_RED = "red"
HEADER_GREY = "grey"


def build_notification_card(title: str, lines: List[str],
                            header_template: str = HEADER_BLUE) -> Dict[str, Any]:
    """构建通用通知卡片

    Args:
        title: 卡片标题
        lines: 正文行（支持 lark_md 语法）
        header_template: 头部颜色模板
    """
    content = "\n".join(lines) if lines else " "
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": header_template,
            "title": {"tag": "plain_text", "content": title},
        },
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": content}},
        ],
    }


def build_task_status_card(task_name: str, old_status: str, new_status: str,
                           operator_name: str = "系统",
                           project_name: str = "") -> Dict[str, Any]:
    """任务状态变更通知卡片"""
    title = f"任务状态更新：{task_name}"
    lines = []
    if project_name:
        lines.append(f"**所属项目**：{project_name}")
    lines.append(f"**状态**：{old_status} → {new_status}")
    lines.append(f"**操作人**：{operator_name}")
    return build_notification_card(title, lines, HEADER_BLUE)


def build_risk_card(risk_title: str, old_status: str, new_status: str,
                    operator_name: str = "系统",
                    project_name: str = "") -> Dict[str, Any]:
    """风险变更通知卡片"""
    title = f"风险更新：{risk_title}"
    lines = []
    if project_name:
        lines.append(f"**所属项目**：{project_name}")
    lines.append(f"**状态**：{old_status} → {new_status}")
    lines.append(f"**操作人**：{operator_name}")
    # 已解决用绿色，其余用橙色提醒
    template = HEADER_GREEN if new_status == "resolved" else HEADER_ORANGE
    return build_notification_card(title, lines, template)


def build_project_card(project_name: str, status: str, completion: int,
                       owner_name: str = "") -> Dict[str, Any]:
    """项目进度通知卡片"""
    title = f"项目进度：{project_name}"
    lines = [
        f"**状态**：{status}",
        f"**完成度**：{completion}%",
    ]
    if owner_name:
        lines.append(f"**负责人**：{owner_name}")
    return build_notification_card(title, lines, HEADER_BLUE)
