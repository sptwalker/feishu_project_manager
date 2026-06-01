# 数据库全量导出 / 导入 — 设计文档

- 日期：2026-06-01
- 状态：已确认，进入实现

## 概述
管理员可在「系统设置 › 其他设置」一键导出全库为 JSON 快照下载，复制到服务端后上传导入（全量替换），实现环境间数据迁移。

## 已确认决策
1. 导出格式：**JSON 快照**（单文件，跨环境、不受 SQLite 文件锁影响、与运行中应用兼容）。
2. 导入策略：**全量替换**（事务内先删后插，失败回滚）。
3. 触发方式：**管理员 UI 按钮**（其他设置页）。
4. 导出范围：7 张业务表全含（含 users、system_settings）。
5. 不做跨版本兼容转换：校验 `version`，schema 不符则安全失败回滚。
6. 导入后**无需重启**（走 ORM 事务）。

## ① 导出格式（JSON 快照）
```json
{
  "version": 1,
  "exported_at": "2026-06-01T14:00:00",
  "app_version": "1.0.0",
  "tables": {
    "users": [...], "departments": [...], "projects": [...],
    "tasks": [...], "risks": [...], "events": [...], "system_settings": [...]
  }
}
```
- 覆盖 7 张业务表；不含 `alembic_version`（保留目标库迁移状态）。
- 每行按模型列序列化：`date`/`datetime` → ISO 字符串、`JSON` 列原样、枚举 → value。

## ② 导入策略（全量替换，事务内）
1. 校验 JSON 结构与 `version`。
2. 事务内：按 FK 依赖逆序删除（events/tasks/risks → projects → departments/users/system_settings），再按正序插入。
3. 出错整体回滚，原数据不受影响。
4. 成功返回各表导入行数。
- 用「先删后插 + 显式列赋值」保留 id、跨环境一致。

## ③ 后端
**`backend/services/backup_service.py`**
- `EXPORT_ORDER`：表插入顺序（删除时逆序）；表名 → 模型映射。
- `export_all(db) -> dict`：输出快照结构。
- `import_all(db, payload) -> dict`：校验 → 事务清空+导入 → 返回 `{table: count}`。
- 行序列化/反序列化集中处理（列遍历、类型转换）。

**`backend/api/v1/backup.py`**（均 `get_current_admin`）
- `GET /backup/export` → JSON 文件下载（`Content-Disposition: attachment; filename="feishu_pm_backup_YYYYMMDD_HHMMSS.json"`）。
- `POST /backup/import`（上传 .json）→ 校验+替换，返回各表行数；格式错误 400，事务失败 500 回滚。
- main.py 注册路由（注意与 settings 同样避免命名冲突，用别名导入）。

## ④ 前端
**`OtherSettings.vue`** 新增「数据备份」卡片（仅管理员可见可用）：
- 导出按钮：`GET /backup/export`（`responseType:'blob'`）触发下载。
- 导入按钮：选 `.json` → 二次确认（强提示"将清空并覆盖当前所有数据，不可恢复"）→ 上传 → 成功提示各表行数并刷新。
- `settingsApi` 加 `exportBackup()` / `importBackup(file)`。

## ⑤ 权限 / 错误
- 两端点仅管理员（非管理员 403）。
- 导入 JSON 解析失败/缺 `tables`/`version` 不符 → 400。
- 导入事务失败 → 回滚 + 500，不留半套数据。

## ⑥ 测试
- 后端：`export_all` 结构正确；`import_all` 全量替换后行数/内容一致；坏 JSON 报错回滚；端点权限（管理员 200 / 非管理员 403）。
- 往返：export → 清库 → import → 数据与原一致。
