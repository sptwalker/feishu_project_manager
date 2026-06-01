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


def build_reminder_card(title: str, lines: List[str],
                        urgent: bool = False) -> Dict[str, Any]:
    """提醒类卡片（逾期/临期/里程碑/跟催）。urgent 为真用红色，否则橙色。"""
    template = HEADER_RED if urgent else HEADER_ORANGE
    return build_notification_card(title, lines, template)


def _owner_mention(owner_name: str, owner_feishu_id: str = "") -> str:
    """负责人 @ 标记：有飞书 id 用 <at> 真正 @ 个人，否则文字提名"""
    if owner_feishu_id:
        # 飞书卡片 lark_md 的 at 语法
        return f'<at id="{owner_feishu_id}"></at>'
    if owner_name:
        return f"**@{owner_name}**"
    return "**@未指定负责人**"


def build_project_followup_card(items: List[Dict[str, Any]],
                                frontend_url: str = "") -> Dict[str, Any]:
    """构建项目进展催办群卡片。

    items: [{project, owner_name, owner_feishu_id, stall_days, no_progress,
             pending_list, reasons}]，project 为 ORM 对象或含 name/id 的字典。
    """
    count = len(items)
    title = f"项目进展待跟进（{count}）"
    elements: List[Dict[str, Any]] = [
        {"tag": "div", "text": {"tag": "lark_md",
         "content": f"以下 **{count}** 个项目需要关注，请相关负责人及时更新进展或处理阻塞："}},
        {"tag": "hr"},
    ]

    for entry in items:
        proj = entry.get("project")
        name = getattr(proj, "name", None) or (proj.get("name") if isinstance(proj, dict) else "未命名项目")
        pid = getattr(proj, "id", None) or (proj.get("id") if isinstance(proj, dict) else None)
        mention = _owner_mention(entry.get("owner_name") or "", entry.get("owner_feishu_id") or "")
        reasons = entry.get("reasons") or []

        lines = [f"**{name}** · 负责人 {mention}"]
        for r in reasons:
            lines.append(f"  · {r}")
        if frontend_url and pid is not None:
            lines.append(f"  · [查看详情]({frontend_url}/?project={pid})")
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(lines)}})

    elements.append({"tag": "hr"})
    elements.append({"tag": "note", "elements": [
        {"tag": "lark_md", "content": "由项目管理系统自动发送 · 请及时更新进展记录"},
    ]})

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": HEADER_ORANGE,
            "title": {"tag": "plain_text", "content": title},
        },
        "elements": elements,
    }
