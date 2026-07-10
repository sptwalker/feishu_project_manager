"""本地开发用「管理员登录」脚本（免飞书）。

用与运行中后端相同的 SECRET_KEY 签发 JWT（读同一份配置/.env），打印一段可直接
粘贴到浏览器控制台的代码，把 token 写进 localStorage（键 fpm_access_token /
fpm_refresh_token）并跳转首页，从而免飞书登录进入本地测试站。

不改后端代码、不加后门接口；仅本地 DB + 本地 token。生产环境勿用。

用法（在仓库根目录执行）：
    python scripts/dev_login.py                # 取任一启用中的管理员（无则创建「刘丹」）
    python scripts/dev_login.py --name 刘丹    # 指定管理员姓名（本地无此人则创建）
"""
import argparse
import os
import sys

# 允许 `python scripts/dev_login.py` 直接运行：把仓库根目录加入模块搜索路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db.session import SessionLocal
from backend.models.user import User, UserRole, UserStatus
from backend.core.security import create_access_token, create_refresh_token


def main() -> None:
    ap = argparse.ArgumentParser(description="本地免飞书管理员登录，签发 JWT 并打印控制台片段")
    ap.add_argument("--name", default=None, help="管理员姓名（本地无此人则新建为管理员）")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        if args.name:
            user = db.query(User).filter(User.name == args.name).first()
            if user is None:
                user = User(feishu_user_id=f"local_{args.name}", name=args.name,
                            role=UserRole.ADMIN, status=UserStatus.ACTIVE)
                db.add(user); db.commit(); db.refresh(user)
                print(f"[created] 新建本地管理员：{args.name} (id={user.id})")
        else:
            user = (db.query(User)
                    .filter(User.role == UserRole.ADMIN, User.status == UserStatus.ACTIVE)
                    .order_by(User.id).first())
            if user is None:
                user = User(feishu_user_id="local_admin", name="刘丹",
                            role=UserRole.ADMIN, status=UserStatus.ACTIVE)
                db.add(user); db.commit(); db.refresh(user)
                print(f"[created] 无管理员，新建本地管理员：刘丹 (id={user.id})")

        # 确保目标账号是「启用中的管理员」
        changed = False
        if user.role != UserRole.ADMIN:
            user.role = UserRole.ADMIN; changed = True
        if user.status != UserStatus.ACTIVE:
            user.status = UserStatus.ACTIVE; changed = True
        if changed:
            db.commit(); db.refresh(user)

        access = create_access_token(data={"sub": str(user.id)})
        refresh = create_refresh_token(data={"sub": str(user.id)})
        uid, uname = user.id, user.name
    finally:
        db.close()

    snippet = (
        f"localStorage.setItem('fpm_access_token','{access}');"
        f"localStorage.setItem('fpm_refresh_token','{refresh}');"
        f"location.href='/'"
    )
    print()
    print(f"管理员：{uname}  (id={uid}, role=admin, status=active)")
    print("步骤：浏览器打开 http://localhost:3000 → 按 F12 打开 Console → 粘贴下面一整行回车：")
    print()
    print(snippet)
    print()
    print("回车后会自动带 token 跳转首页，即以管理员身份登录。")


if __name__ == "__main__":
    main()
