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


def build_meeting_doc_card(session: int, meeting_date: str, recorder: str,
                           doc_url: str) -> Dict[str, Any]:
    """周会纪要分享卡片（发核心组群），含飞书文档链接。"""
    lines = []
    if meeting_date:
        lines.append(f"**会议日期**：{meeting_date}")
    if recorder:
        lines.append(f"**记录人**：{recorder}")
    lines.append(f"[查看会议记录]({doc_url})")
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": HEADER_BLUE,
            "title": {"tag": "plain_text", "content": f"第 {session} 次周会纪要"},
        },
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(lines)}},
        ],
    }


def build_meeting_open_card(session: int, public_url: str,
                            operator: str = None) -> Dict[str, Any]:
    """周会模式开启通知卡片（发核心组群）。
    operator=None 表示系统自动开启（文案A）；有值表示管理员手动开启（文案C）。"""
    cycle = f"现在已经进入了第{session}次的新周会周期"
    if operator:
        head = f"管理员{operator}开启了核心项目管理系统的周会模式，{cycle}"
    else:
        head = f"请注意：核心项目管理系统的周会模式已开启，{cycle}"
    body = (f"{head}，请各部门和项目负责人及时登录{public_url}"
            "更新自己负责项目的最新进展信息，现在的所有更新内容将被自动收录到新周会记录中，"
            "并在下次周会上集中汇报。")
    return build_notification_card(f"周会模式已开启 · 第 {session} 次", [body], HEADER_GREEN)


def build_meeting_reminder_card(session: int, body: str) -> Dict[str, Any]:
    """周会自动催更卡片（发核心组群）。标题同开启卡片，正文为催更文案。"""
    return build_notification_card(f"周会模式已开启 · 第 {session} 次", [body], HEADER_GREEN)


def build_owner_followup_card(owner: str, project_lines: List[Dict[str, str]],
                              auto: bool = False) -> Dict[str, Any]:
    """按负责人私聊催办卡片（DM）。project_lines: [{name, reason}]。
    auto 决定末句为「自动催办」还是「手动催办」。"""
    lines = [f"{owner}，你好！你目前在周会项目管理系统中有以下待处理项目需要尽快回复进展信息："]
    for p in project_lines:
        lines.append(f"**【{p.get('name', '')}】**（催办原因：{p.get('reason', '')}）")
    tail = "以上信息为自动催办通知，请您重视并及时处理！" if auto else "以上信息为手动催办通知，请您重视并及时处理！"
    lines.append(tail)
    return build_notification_card("周会待处理项目催办通知", lines, HEADER_ORANGE)

