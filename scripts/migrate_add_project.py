"""数据库迁移脚本 - 添加多项目支持"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from shared.config import get_config
from backend.database import get_engine, init_database


def migrate():
    """执行迁移"""
    get_config().load()
    init_database()
    engine = get_engine()

    with engine.connect() as conn:
        # 1. 创建 projects 表
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100) NOT NULL UNIQUE,
                path VARCHAR(500) NOT NULL UNIQUE,
                description TEXT,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))
        conn.commit()
        print("✓ 创建 projects 表")

        # 2. 给 work_sessions 添加 project_id
        try:
            conn.execute(text("""
                ALTER TABLE work_sessions
                ADD COLUMN project_id INTEGER NULL,
                ADD INDEX idx_work_sessions_project_id (project_id),
                ADD CONSTRAINT fk_work_sessions_project
                    FOREIGN KEY (project_id) REFERENCES projects(id)
            """))
            conn.commit()
            print("✓ work_sessions 添加 project_id")
        except Exception as e:
            if "Duplicate column" in str(e):
                print("- work_sessions.project_id 已存在，跳过")
            else:
                raise

        # 3. 给 activities 添加 project_id
        try:
            conn.execute(text("""
                ALTER TABLE activities
                ADD COLUMN project_id INTEGER NULL,
                ADD INDEX idx_activities_project_id (project_id),
                ADD CONSTRAINT fk_activities_project
                    FOREIGN KEY (project_id) REFERENCES projects(id)
            """))
            conn.commit()
            print("✓ activities 添加 project_id")
        except Exception as e:
            if "Duplicate column" in str(e):
                print("- activities.project_id 已存在，跳过")
            else:
                raise

        # 4. 给 journal_entries 添加 project_id
        try:
            conn.execute(text("""
                ALTER TABLE journal_entries
                ADD COLUMN project_id INTEGER NULL,
                ADD INDEX idx_journal_entries_project_id (project_id),
                ADD CONSTRAINT fk_journal_entries_project
                    FOREIGN KEY (project_id) REFERENCES projects(id)
            """))
            conn.commit()
            print("✓ journal_entries 添加 project_id")
        except Exception as e:
            if "Duplicate column" in str(e):
                print("- journal_entries.project_id 已存在，跳过")
            else:
                raise

    print("\n迁移完成！")


if __name__ == "__main__":
    migrate()
