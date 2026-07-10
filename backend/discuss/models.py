"""留言讨论区数据模型（存独立 discuss.db，与 PM 主库零交叉）"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Index

from backend.discuss.db import DiscussBase


class DiscussUser(DiscussBase):
    """外部用户（邮箱验证码注册，无密码）"""
    __tablename__ = "discuss_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(200), unique=True, nullable=False, index=True, comment="邮箱（登录标识）")
    phone = Column(String(30), nullable=False, comment="手机号（注册必填，仅内部可见）")
    nickname = Column(String(50), nullable=False, comment="昵称（公开显示）")
    status = Column(String(20), default="active", nullable=False, comment="active=正常 / blocked=封禁")
    ip_hash = Column(String(64), comment="注册 IP 哈希（限制单 IP 注册量）")
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    last_seen_at = Column(DateTime, comment="最后活跃时刻")


class DiscussCode(DiscussBase):
    """邮箱验证码（10 分钟有效，5 次错误作废；同邮箱重发覆盖旧码）"""
    __tablename__ = "discuss_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(200), unique=True, nullable=False, index=True)
    code_hash = Column(String(64), nullable=False, comment="验证码哈希（不存明文）")
    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, default=0, nullable=False, comment="错误尝试次数（≥5 作废）")
    sent_at = Column(DateTime, default=datetime.now, nullable=False, comment="最近发送时刻（60s 冷却）")
    daily_count = Column(Integer, default=1, nullable=False, comment="当日已发送次数（≤10）")
    daily_date = Column(String(10), comment="daily_count 对应日期 YYYY-MM-DD")


class DiscussBoard(DiscussBase):
    """讨论区（v1 仅一条记录；留言按 board_id 关联，未来多区零迁移）"""
    __tablename__ = "discuss_boards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False, default="用户留言区")
    welcome_text = Column(Text, comment="欢迎语（公开页顶部展示）")
    status = Column(String(20), default="open", nullable=False, comment="open / closed")
    created_at = Column(DateTime, default=datetime.now, nullable=False)


class DiscussMessage(DiscussBase):
    """留言 / 回复（楼结构：thread_id=根留言 id；根留言的 thread_id=自身 id）"""
    __tablename__ = "discuss_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    board_id = Column(Integer, nullable=False, index=True)
    thread_id = Column(Integer, index=True, comment="所属楼（根留言 id；根自指）")
    parent_id = Column(Integer, comment="直接回复的目标留言 id（根留言为 null）")
    author_type = Column(String(10), nullable=False, comment="external / internal")
    ext_user_id = Column(Integer, index=True, comment="外部作者 id（author_type=external）")
    author_name = Column(String(100), nullable=False, comment="显示名（外部昵称 / 内部真名快照）")
    content = Column(Text, nullable=False, comment="正文（纯文本渲染，绝不作为 HTML）")
    # 附件：[{type:'image'|'video', url, name, size}]
    attachments = Column(JSON, default=list, comment="图片/视频附件列表")
    star = Column(Integer, default=0, nullable=False, comment="奖励星级 0-5（内部评定，外部可见）")
    status = Column(String(20), default="visible", nullable=False, comment="visible / hidden")
    replied = Column(Integer, default=0, nullable=False, comment="楼是否已有官方回复（根留言冗余标记：0/1）")
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)


# 常用查询联合索引：楼内取贴、未回复根留言筛选
Index("ix_discuss_msg_thread_time", DiscussMessage.thread_id, DiscussMessage.created_at)
Index("ix_discuss_msg_board_root", DiscussMessage.board_id, DiscussMessage.parent_id, DiscussMessage.replied)
