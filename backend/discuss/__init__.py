"""外部留言讨论区模块（自治包）

与 PM 业务完全隔离：独立 discuss.db、独立媒体目录、独立外部用户 JWT。
仅共享：域名、部署容器、内部飞书登录（admin 接口）、system_settings 里的开关与 SMTP 配置。
"""
