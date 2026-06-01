"""测试批注功能的完整流程"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db.base import Base
from backend.services.project_service import ProjectService
from backend.schemas.project import ProjectCreate, ProjectUpdate


@pytest.fixture
def db_session():
    """数据库会话 fixture"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_annotation_persistence(db_session):
    """测试批注在数据库中的持久化"""
    # 1. 创建项目，带一条进展记录
    project_data = ProjectCreate(
        name="批注测试项目",
        urgency="medium",
        progress_log=[
            {
                "time": "2026-06-01 10:00",
                "content": "初始进展",
                "status": "正常",
                "id": "entry-1"
            }
        ]
    )
    project = ProjectService.create(db_session, project_data)
    project_id = project.id

    # 验证初始状态：无批注
    assert project.progress_log[0]["annotations"] is None

    # 2. 添加批注
    update_data = ProjectUpdate(
        progress_log=[
            {
                "time": "2026-06-01 10:00",
                "content": "初始进展",
                "status": "正常",
                "id": "entry-1",
                "annotations": [
                    {
                        "id": "ann-1",
                        "author_name": "张三",
                        "content": "这个进展需要补充细节",
                        "created_at": "2026-06-01 11:00",
                        "replies": []
                    }
                ]
            }
        ]
    )
    updated = ProjectService.update(db_session, project_id, update_data)
    assert updated.progress_log[0]["annotations"][0]["author_name"] == "张三"

    # 3. 模拟刷新：清空 session 缓存，重新读取
    db_session.expire_all()
    reloaded = ProjectService.get_by_id(db_session, project_id)

    # 验证批注持久化成功
    assert reloaded is not None
    assert len(reloaded.progress_log) == 1
    assert reloaded.progress_log[0]["annotations"] is not None
    assert len(reloaded.progress_log[0]["annotations"]) == 1
    assert reloaded.progress_log[0]["annotations"][0]["author_name"] == "张三"
    assert reloaded.progress_log[0]["annotations"][0]["content"] == "这个进展需要补充细节"

    # 4. 添加回复
    update_data2 = ProjectUpdate(
        progress_log=[
            {
                "time": "2026-06-01 10:00",
                "content": "初始进展",
                "status": "正常",
                "id": "entry-1",
                "annotations": [
                    {
                        "id": "ann-1",
                        "author_name": "张三",
                        "content": "这个进展需要补充细节",
                        "created_at": "2026-06-01 11:00",
                        "replies": [
                            {
                                "id": "reply-1",
                                "author_name": "李四",
                                "content": "已补充，请查看",
                                "created_at": "2026-06-01 12:00"
                            }
                        ]
                    }
                ]
            }
        ]
    )
    updated2 = ProjectService.update(db_session, project_id, update_data2)

    # 5. 再次刷新验证回复持久化
    db_session.expire_all()
    reloaded2 = ProjectService.get_by_id(db_session, project_id)

    assert reloaded2.progress_log[0]["annotations"][0]["replies"] is not None
    assert len(reloaded2.progress_log[0]["annotations"][0]["replies"]) == 1
    assert reloaded2.progress_log[0]["annotations"][0]["replies"][0]["author_name"] == "李四"
    assert reloaded2.progress_log[0]["annotations"][0]["replies"][0]["content"] == "已补充，请查看"

    # 清理
    ProjectService.delete(db_session, project_id)


def test_multiple_annotations_on_single_entry(db_session):
    """测试单条进展记录支持多条批注"""
    project_data = ProjectCreate(
        name="多批注测试",
        urgency="medium",
        progress_log=[{"time": "2026-06-01 10:00", "content": "进展A", "status": "正常", "id": "e1"}]
    )
    project = ProjectService.create(db_session, project_data)

    # 添加3条批注
    update_data = ProjectUpdate(
        progress_log=[
            {
                "time": "2026-06-01 10:00",
                "content": "进展A",
                "status": "正常",
                "id": "e1",
                "annotations": [
                    {"id": "a1", "author_name": "用户1", "content": "批注1", "created_at": "2026-06-01 11:00"},
                    {"id": "a2", "author_name": "用户2", "content": "批注2", "created_at": "2026-06-01 11:30"},
                    {"id": "a3", "author_name": "用户3", "content": "批注3", "created_at": "2026-06-01 12:00"},
                ]
            }
        ]
    )
    ProjectService.update(db_session, project.id, update_data)

    db_session.expire_all()
    reloaded = ProjectService.get_by_id(db_session, project.id)

    assert len(reloaded.progress_log[0]["annotations"]) == 3
    assert reloaded.progress_log[0]["annotations"][0]["author_name"] == "用户1"
    assert reloaded.progress_log[0]["annotations"][1]["author_name"] == "用户2"
    assert reloaded.progress_log[0]["annotations"][2]["author_name"] == "用户3"

    ProjectService.delete(db_session, project.id)


def test_annotation_on_multiple_entries(db_session):
    """测试多条进展记录各自独立批注"""
    project_data = ProjectCreate(
        name="多进展批注测试",
        urgency="medium",
        progress_log=[
            {"time": "2026-06-01 10:00", "content": "进展1", "status": "正常", "id": "e1"},
            {"time": "2026-06-01 11:00", "content": "进展2", "status": "正常", "id": "e2"},
        ]
    )
    project = ProjectService.create(db_session, project_data)

    # 给两条进展分别添加批注
    update_data = ProjectUpdate(
        progress_log=[
            {
                "time": "2026-06-01 10:00",
                "content": "进展1",
                "status": "正常",
                "id": "e1",
                "annotations": [{"id": "a1", "author_name": "张三", "content": "批注A", "created_at": "2026-06-01 12:00"}]
            },
            {
                "time": "2026-06-01 11:00",
                "content": "进展2",
                "status": "正常",
                "id": "e2",
                "annotations": [{"id": "a2", "author_name": "李四", "content": "批注B", "created_at": "2026-06-01 13:00"}]
            },
        ]
    )
    ProjectService.update(db_session, project.id, update_data)

    db_session.expire_all()
    reloaded = ProjectService.get_by_id(db_session, project.id)

    assert reloaded.progress_log[0]["annotations"][0]["content"] == "批注A"
    assert reloaded.progress_log[1]["annotations"][0]["content"] == "批注B"

    ProjectService.delete(db_session, project.id)


def test_annotation_survives_progress_edit(db_session):
    """测试批注在进展编辑后依然保留（模拟前端进入/退出编辑模式）"""
    # 创建项目，带批注
    project_data = ProjectCreate(
        name="编辑模式测试",
        urgency="medium",
        progress_log=[
            {
                "time": "2026-06-01 10:00",
                "content": "初始进展",
                "status": "正常",
                "id": "e1",
                "annotations": [
                    {
                        "id": "a1",
                        "author_name": "张三",
                        "content": "重要批注",
                        "created_at": "2026-06-01 11:00",
                        "replies": [
                            {"id": "r1", "author_name": "李四", "content": "已阅", "created_at": "2026-06-01 12:00"}
                        ]
                    }
                ]
            }
        ]
    )
    project = ProjectService.create(db_session, project_data)

    # 模拟前端：读取 → 进入编辑模式（深拷贝）→ 修改进展内容 → 保存
    db_session.expire_all()
    loaded = ProjectService.get_by_id(db_session, project.id)

    # 深拷贝模拟 progressDraft（前端行为）
    import json
    draft = json.loads(json.dumps(loaded.progress_log))

    # 修改进展内容（但不修改批注）
    draft[0]["content"] = "更新后的进展"

    # 保存（模拟 cleanDraft + commitProgress）
    update_data = ProjectUpdate(progress_log=draft)
    ProjectService.update(db_session, project.id, update_data)

    # 验证：批注和回复依然存在
    db_session.expire_all()
    final = ProjectService.get_by_id(db_session, project.id)

    assert final.progress_log[0]["content"] == "更新后的进展"
    assert final.progress_log[0]["annotations"] is not None
    assert len(final.progress_log[0]["annotations"]) == 1
    assert final.progress_log[0]["annotations"][0]["content"] == "重要批注"
    assert len(final.progress_log[0]["annotations"][0]["replies"]) == 1
    assert final.progress_log[0]["annotations"][0]["replies"][0]["content"] == "已阅"

    ProjectService.delete(db_session, project.id)


def test_document_attachment_persistence(db_session):
    """测试文档附件在数据库中的持久化"""
    # 创建项目，带文档附件
    project_data = ProjectCreate(
        name="文档附件测试",
        urgency="medium",
        progress_log=[
            {
                "time": "2026-06-01 10:00",
                "content": "完成设计文档",
                "status": "正常",
                "id": "e1",
                "attachments": [
                    {
                        "url": "https://example.feishu.cn/docx/abc123",
                        "title": "设计方案V1",
                        "added_at": "2026-06-01 10:30"
                    }
                ]
            }
        ]
    )
    project = ProjectService.create(db_session, project_data)
    
    # 验证附件保存成功
    assert project.progress_log[0]["attachments"] is not None
    assert len(project.progress_log[0]["attachments"]) == 1
    assert project.progress_log[0]["attachments"][0]["url"] == "https://example.feishu.cn/docx/abc123"
    assert project.progress_log[0]["attachments"][0]["title"] == "设计方案V1"
    
    # 刷新验证持久化
    db_session.expire_all()
    reloaded = ProjectService.get_by_id(db_session, project.id)
    
    assert reloaded.progress_log[0]["attachments"] is not None
    assert len(reloaded.progress_log[0]["attachments"]) == 1
    assert reloaded.progress_log[0]["attachments"][0]["url"] == "https://example.feishu.cn/docx/abc123"
    
    # 添加第二个附件
    update_data = ProjectUpdate(
        progress_log=[
            {
                "time": "2026-06-01 10:00",
                "content": "完成设计文档",
                "status": "正常",
                "id": "e1",
                "attachments": [
                    {
                        "url": "https://example.feishu.cn/docx/abc123",
                        "title": "设计方案V1",
                        "added_at": "2026-06-01 10:30"
                    },
                    {
                        "url": "https://example.feishu.cn/docs/xyz789",
                        "title": "技术评审记录",
                        "added_at": "2026-06-01 14:00"
                    }
                ]
            }
        ]
    )
    ProjectService.update(db_session, project.id, update_data)
    
    # 验证多个附件
    db_session.expire_all()
    final = ProjectService.get_by_id(db_session, project.id)
    
    assert len(final.progress_log[0]["attachments"]) == 2
    assert final.progress_log[0]["attachments"][1]["title"] == "技术评审记录"
    
    ProjectService.delete(db_session, project.id)
