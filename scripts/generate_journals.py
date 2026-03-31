"""通过 Claude CLI 生成 per-day 工作日志

用法:
    # 交互模式
    python scripts/generate_journals.py

    # 指定参数
    python scripts/generate_journals.py --project 5 --from 2026-03-10 --to 2026-03-25

    # 指定输出文件
    python scripts/generate_journals.py --project 5 --output my-journals.md
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from backend.database import get_db_session, init_database
from backend.services.ssh_tunnel import cleanup_tunnel
from shared.config import get_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# 排除的文件路径模式
EXCLUDED_PATH_PATTERNS = [".tmp", ".playwright", ".venv", "__pycache__", "node_modules", ".git/"]


def parse_args():
    parser = argparse.ArgumentParser(description="Generate per-day work journals via Claude CLI")
    parser.add_argument("--project", type=str, help="Project ID or name (omit for interactive selection)")
    parser.add_argument("--from", dest="from_date", type=str, help="Start date (YYYY-MM-DD), default: 30 days ago")
    parser.add_argument("--to", dest="to_date", type=str, help="End date (YYYY-MM-DD), default: today")
    parser.add_argument("--output", "-o", type=str, help="Output markdown file path")
    return parser.parse_args()


def interactive_select(projects):
    """交互式选择项目"""
    print("\nAvailable projects:")
    for p in projects:
        print(f"  [{p['id']}] {p['name']}")

    choice = input("\nSelect project ID (or 'all'): ").strip()
    if choice.lower() == "all":
        return None
    try:
        pid = int(choice)
        if any(p["id"] == pid for p in projects):
            return pid
    except ValueError:
        # 按名称匹配
        matches = [p for p in projects if p["name"] == choice]
        if matches:
            return matches[0]["id"]
    print("Invalid selection.")
    sys.exit(1)


def fetch_projects():
    """获取所有项目"""
    with get_db_session() as session:
        result = session.execute(text("SELECT id, name, description FROM projects ORDER BY id"))
        return [{"id": row[0], "name": row[1], "description": row[2]} for row in result]


def resolve_project(project_arg, projects):
    """解析项目参数为 project_id"""
    if project_arg is None:
        return None  # all projects
    try:
        pid = int(project_arg)
        if any(p["id"] == pid for p in projects):
            return pid
    except ValueError:
        matches = [p for p in projects if p["name"] == project_arg]
        if matches:
            return matches[0]["id"]
    print(f"Project '{project_arg}' not found.")
    sys.exit(1)


def fetch_distinct_days(project_id, from_date, to_date):
    """获取有活动记录的日期列表"""
    with get_db_session() as session:
        if project_id:
            result = session.execute(
                text(
                    "SELECT DISTINCT DATE(timestamp) as day FROM activities "
                    "WHERE project_id = :pid AND DATE(timestamp) BETWEEN :fd AND :td "
                    "ORDER BY day"
                ),
                {"pid": project_id, "fd": from_date, "td": to_date},
            )
        else:
            result = session.execute(
                text(
                    "SELECT DISTINCT DATE(timestamp) as day FROM activities "
                    "WHERE DATE(timestamp) BETWEEN :fd AND :td "
                    "ORDER BY day"
                ),
                {"fd": from_date, "td": to_date},
            )
        return [row[0] for row in result]


def fetch_day_data(project_id, day):
    """拉取某一天的完整数据"""
    data = {"day": str(day)}

    with get_db_session() as session:
        # 1. 活动汇总
        if project_id:
            result = session.execute(
                text(
                    "SELECT activity_type, COUNT(*) as cnt, "
                    "MIN(TIME(timestamp)) as first_act, MAX(TIME(timestamp)) as last_act "
                    "FROM activities "
                    "WHERE project_id = :pid AND DATE(timestamp) = :day "
                    "GROUP BY activity_type"
                ),
                {"pid": project_id, "day": day},
            )
        else:
            result = session.execute(
                text(
                    "SELECT activity_type, COUNT(*) as cnt, "
                    "MIN(TIME(timestamp)) as first_act, MAX(TIME(timestamp)) as last_act "
                    "FROM activities "
                    "WHERE DATE(timestamp) = :day "
                    "GROUP BY activity_type"
                ),
                {"day": day},
            )
        data["activity_summary"] = [
            {
                "type": row[0],
                "count": row[1],
                "first": str(row[2]),
                "last": str(row[3]),
            }
            for row in result
        ]

        # 2. Git commits
        if project_id:
            result = session.execute(
                text(
                    "SELECT timestamp, description, metadata "
                    "FROM activities "
                    "WHERE project_id = :pid AND DATE(timestamp) = :day "
                    "AND activity_type = 'git_commit' "
                    "ORDER BY timestamp"
                ),
                {"pid": project_id, "day": day},
            )
        else:
            result = session.execute(
                text(
                    "SELECT timestamp, description, metadata "
                    "FROM activities "
                    "WHERE DATE(timestamp) = :day "
                    "AND activity_type = 'git_commit' "
                    "ORDER BY timestamp"
                ),
                {"day": day},
            )
        commits = []
        for row in result:
            meta = row[2] or {}
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except (json.JSONDecodeError, TypeError):
                    meta = {}
            commits.append(
                {
                    "time": str(row[0]),
                    "message": row[1],
                    "hash": meta.get("commit_hash", ""),
                    "files": meta.get("changed_files", []),
                    "stats": meta.get("stats", {}),
                }
            )
        data["git_commits"] = commits

        # 3. 文件操作按目录聚合
        if project_id:
            result = session.execute(
                text(
                    "SELECT metadata, activity_type FROM activities "
                    "WHERE project_id = :pid AND DATE(timestamp) = :day "
                    "AND activity_type IN ('file_create', 'file_modify', 'file_delete') "
                    "AND metadata IS NOT NULL"
                ),
                {"pid": project_id, "day": day},
            )
        else:
            result = session.execute(
                text(
                    "SELECT metadata, activity_type FROM activities "
                    "WHERE DATE(timestamp) = :day "
                    "AND activity_type IN ('file_create', 'file_modify', 'file_delete') "
                    "AND metadata IS NOT NULL"
                ),
                {"day": day},
            )

        dir_ops = {}  # dir -> {type -> count, files -> set}
        for row in result:
            meta = row[0] or {}
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except (json.JSONDecodeError, TypeError):
                    continue
            filepath = meta.get("filepath", "")
            if not filepath:
                continue
            # 排除模式
            if any(pat in filepath for pat in EXCLUDED_PATH_PATTERNS):
                continue

            # 提取有意义的路径部分
            # 尝试提取项目名之后的路径
            parts = filepath.replace("\\", "/").split("/")
            # 找到有意义的项目目录层级
            proj_idx = None
            for i, p in enumerate(parts):
                if p in ("Development", "DEV"):
                    proj_idx = i + 1
                    break
            if proj_idx and proj_idx < len(parts):
                rel_path = "/".join(parts[proj_idx:])
            else:
                rel_path = parts[-1] if parts else filepath

            dir_name = rel_path.split("/")[0] if "/" in rel_path else "(root)"
            file_name = parts[-1] if parts else filepath

            if dir_name not in dir_ops:
                dir_ops[dir_name] = {"counts": {}, "files": set()}
            act_type = row[1]
            dir_ops[dir_name]["counts"][act_type] = dir_ops[dir_name]["counts"].get(act_type, 0) + 1
            if len(dir_ops[dir_name]["files"]) < 15:
                dir_ops[dir_name]["files"].add(file_name)

        data["dir_operations"] = {
            k: {
                "counts": v["counts"],
                "total": sum(v["counts"].values()),
                "files": sorted(v["files"])[:10],
            }
            for k, v in sorted(dir_ops.items(), key=lambda x: -sum(x[1]["counts"].values()))
        }

        # 4. 工作时段
        if project_id:
            result = session.execute(
                text(
                    "SELECT start_time, end_time FROM work_sessions "
                    "WHERE project_id = :pid AND DATE(start_time) <= :day "
                    "AND (DATE(end_time) >= :day OR end_time IS NULL)"
                ),
                {"pid": project_id, "day": day},
            )
        else:
            result = session.execute(
                text(
                    "SELECT start_time, end_time FROM work_sessions "
                    "WHERE DATE(start_time) <= :day "
                    "AND (DATE(end_time) >= :day OR end_time IS NULL)"
                ),
                {"day": day},
            )
        data["work_sessions"] = [
            {"start": str(row[0]), "end": str(row[1]) if row[1] else "(ongoing)"} for row in result
        ]

    return data


def format_data_for_claude(project_name, project_id, days_data):
    """将数据格式化为 Claude 可理解的结构化文本"""
    lines = []
    lines.append(f"PROJECT: {project_name} (id={project_id})")
    lines.append(f"Total days with activity: {len(days_data)}")
    lines.append("")

    for day_data in days_data:
        day = day_data["day"]
        lines.append(f"=== {day} ===")

        # 时间范围和总活动数
        summary = day_data["activity_summary"]
        if summary:
            all_first = min(s["first"] for s in summary)
            all_last = max(s["last"] for s in summary)
            total = sum(s["count"] for s in summary)
            lines.append(f"Time range: {all_first[:5]} - {all_last[:5]} | Total activities: {total}")
        else:
            lines.append("Time range: N/A | Total activities: 0")

        # 工作时段
        sessions = day_data["work_sessions"]
        if sessions:
            sess_strs = [f"{s['start'][11:16]}-{s['end'][11:16]}" for s in sessions]
            lines.append(f"Work sessions: {', '.join(sess_strs)}")

        # 活动类型分布
        if summary:
            lines.append("")
            lines.append("Activity breakdown:")
            for s in sorted(summary, key=lambda x: -x["count"]):
                lines.append(f"  {s['type']}: {s['count']}")

        # 目录级文件操作
        dir_ops = day_data["dir_operations"]
        if dir_ops:
            lines.append("")
            lines.append("Key directories by file operations:")
            for dir_name, info in list(dir_ops.items())[:8]:
                files_str = ", ".join(info["files"][:6])
                if len(info["files"]) > 6:
                    files_str += ", ..."
                lines.append(f"  {dir_name}/: {info['total']} ops  ({files_str})")

        # Git commits
        commits = day_data["git_commits"]
        lines.append("")
        lines.append(f"Git commits ({len(commits)}):")
        if commits:
            for c in commits:
                stats = c["stats"]
                short_hash = c["hash"][:7] if c["hash"] else "?"
                msg_first_line = c["message"].split("\n")[0] if c["message"] else "(no message)"
                stats_str = f"+{stats.get('insertions', 0)}/-{stats.get('deletions', 0)} ({stats.get('files', 0)} files)"
                lines.append(f"  [{short_hash}] {msg_first_line}")
                lines.append(f"    Stats: {stats_str}")
                changed = c.get("files", [])
                if changed:
                    for f in changed[:10]:
                        lines.append(f"    - {f}")
                    if len(changed) > 10:
                        lines.append(f"    ... and {len(changed) - 10} more files")
        else:
            lines.append("  (none)")

        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def build_prompt(formatted_data):
    """构建 Claude prompt"""
    return f"""You are a work journal generator. Based on the structured activity data below, generate a per-day work journal in English Markdown format.

RULES:
1. Output in English only.
2. For each day, create a section with:
   - Date (with day of week)
   - Work type (one of: Development, Meeting, Research, Testing, Documentation, Other)
   - Time range and total activity count
   - A 2-4 sentence summary describing what was done, based on git commit messages, file paths, and directory operations. Be specific about what was built, fixed, or changed.
   - "Key outputs" as a bullet list of concrete deliverables
3. Group consecutive days under the same project header.
4. Be concise but specific — mention actual file names, commit messages, and technical details from the data.
5. Use standard Markdown formatting (## for days, **bold** for emphasis, - for bullet lists).
6. Do NOT include any introductory or concluding remarks — just the journal entries.
7. If a day has very few activities (<5 total), still generate an entry but note it was light activity.

ACTIVITY DATA:

{formatted_data}"""


def call_claude_cli(prompt):
    """调用 claude CLI 生成日志"""
    logger.info("Calling Claude CLI to generate journals...")
    try:
        result = subprocess.run(
            ["claude", "--print", prompt],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            logger.error(f"Claude CLI error: {result.stderr}")
            return None
        return result.stdout
    except FileNotFoundError:
        logger.error("'claude' CLI not found. Please install Claude Code CLI first.")
        return None
    except subprocess.TimeoutExpired:
        logger.error("Claude CLI timed out (600s).")
        return None


def main():
    args = parse_args()

    # 初始化数据库
    get_config()
    init_database()

    try:
        # 获取项目列表
        projects = fetch_projects()
        if not projects:
            print("No projects found in database.")
            return

        # 解析项目
        if args.project:
            project_id = resolve_project(args.project, projects)
        elif sys.stdin.isatty():
            project_id = interactive_select(projects)
        else:
            project_id = None  # all

        # 解析日期
        to_date = args.to_date or datetime.now().strftime("%Y-%m-%d")
        from_date = args.from_date or (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        print(f"Date range: {from_date} to {to_date}")

        # 确定项目和名称
        if project_id:
            proj_info = next(p for p in projects if p["id"] == project_id)
            project_name = proj_info["name"]
        else:
            project_name = "All-Projects"
            project_id = None

        # 获取有记录的日期
        days = fetch_distinct_days(project_id, from_date, to_date)
        if not days:
            print("No activity found in the given date range.")
            return

        print(f"Found {len(days)} days with activity")

        # 拉取每天的数据
        all_days_data = []
        for day in days:
            logger.info(f"Fetching data for {day}...")
            day_data = fetch_day_data(project_id, day)
            all_days_data.append(day_data)

        # 格式化数据
        formatted = format_data_for_claude(project_name, project_id or 0, all_days_data)

        # 构建 prompt
        prompt = build_prompt(formatted)

        # 调用 Claude CLI
        markdown = call_claude_cli(prompt)
        if not markdown:
            print("Failed to generate journals.")
            # 保存原始数据供调试
            debug_path = f"journals-{project_name}-debug.txt"
            with open(debug_path, "w") as f:
                f.write(prompt)
            print(f"Raw data saved to {debug_path}")
            return

        # 添加项目标题
        header = f"# Work Journal - {project_name}\n\n"
        header += f"**Period**: {from_date} to {to_date}\n\n---\n\n"
        full_output = header + markdown

        # 保存文件
        if args.output:
            output_path = args.output
        else:
            output_path = f"journals-{project_name}-{from_date}-{to_date}.md"

        with open(output_path, "w") as f:
            f.write(full_output)
        print(f"\nJournals saved to: {output_path}")

    finally:
        cleanup_tunnel()


if __name__ == "__main__":
    main()
