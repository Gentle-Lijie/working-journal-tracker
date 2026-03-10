"""数据库迁移脚本 - 移除 projects.path 列，路径信息迁移到本地 path_map.yaml"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from backend.database import get_engine, init_database
from shared.config import get_config
from shared.path_map import get_path_map


def migrate():
    """执行迁移"""
    get_config().load()
    init_database()
    engine = get_engine()
    path_map = get_path_map()

    with engine.connect() as conn:
        # 1. 检查 path 列是否存在
        result = conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name = 'projects' AND column_name = 'path'"
        ))
        has_path_column = result.scalar() > 0

        if not has_path_column:
            print("- projects.path 列已不存在，跳过迁移")
            return

        # 2. 导出现有路径到本地 path_map.yaml
        rows = conn.execute(text("SELECT name, path FROM projects WHERE path IS NOT NULL"))
        existing_map = path_map.get_all()
        count = 0
        for name, path in rows:
            if name not in existing_map:
                path_map.set_path(name, path)
                count += 1
                print(f"  导出: {name} -> {path}")
            else:
                print(f"  跳过（已存在）: {name} -> {existing_map[name]}")
        print(f"✓ 导出 {count} 条路径映射到 path_map.yaml")

        # 3. 删除 path 列的唯一索引
        # 查找索引名称
        idx_result = conn.execute(text(
            "SELECT INDEX_NAME FROM information_schema.statistics "
            "WHERE table_name = 'projects' AND column_name = 'path' "
            "AND NON_UNIQUE = 0"
        ))
        for (idx_name,) in idx_result:
            conn.execute(text(f"ALTER TABLE projects DROP INDEX `{idx_name}`"))
            print(f"✓ 删除索引: {idx_name}")
        conn.commit()

        # 4. 删除 path 列
        conn.execute(text("ALTER TABLE projects DROP COLUMN path"))
        conn.commit()
        print("✓ 删除 projects.path 列")

    print("\n迁移完成！路径信息已保存到本地 ~/.work-journal/path_map.yaml")


if __name__ == "__main__":
    migrate()
