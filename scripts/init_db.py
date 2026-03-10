#!/usr/bin/env python3
"""数据库初始化脚本"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import create_tables, init_database
from shared.config import get_config


def main():
    print("正在初始化数据库...")

    # 加载配置
    config = get_config()
    config.load()

    print(f"数据库配置:")
    print(f"  主机: {config.database['host']}")
    print(f"  端口: {config.database['port']}")
    print(f"  数据库: {config.database['database']}")
    print(f"  用户: {config.database['user']}")

    # 如果启用SSH隧道，先建立隧道获取本地端口
    ssh_config = config.ssh
    if ssh_config.get("enabled"):
        from backend.services.ssh_tunnel import get_tunnel_manager
        tunnel_manager = get_tunnel_manager()
        host, port = tunnel_manager.start(ssh_config)
    else:
        host = config.database["host"]
        port = config.database["port"]

    # 先创建数据库（如果不存在）
    import pymysql
    db_name = config.database["database"]
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=config.database["user"],
            password=config.database["password"],
        )
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.close()
        print(f"✓ 数据库 '{db_name}' 已就绪")
    except Exception as e:
        print(f"✗ 创建数据库失败: {e}")
        sys.exit(1)

    # 初始化数据库连接
    try:
        init_database()
        print("✓ 数据库连接成功")
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        sys.exit(1)

    # 创建表
    try:
        create_tables()
        print("✓ 数据库表创建成功")
    except Exception as e:
        print(f"✗ 创建表失败: {e}")
        sys.exit(1)

    print("\n数据库初始化完成！")


if __name__ == "__main__":
    main()
