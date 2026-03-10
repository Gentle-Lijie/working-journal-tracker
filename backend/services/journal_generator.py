"""日志生成服务"""

import logging
from datetime import datetime

from backend.database import get_db_session
from backend.models.activity import Activity
from backend.models.journal_entry import JournalEntry
from backend.services.ai_service import get_ai_service
from shared.utils import format_datetime

logger = logging.getLogger(__name__)


class JournalGenerator:
    """日志生成器"""

    def __init__(self):
        self.ai_service = get_ai_service()

    def generate(
        self,
        start_time: datetime,
        end_time: datetime,
        session_id: int | None = None,
    ) -> JournalEntry | None:
        """生成指定时间范围的日志条目"""

        # 查询活动记录
        with get_db_session() as db_session:
            query = db_session.query(Activity).filter(
                Activity.timestamp >= start_time,
                Activity.timestamp <= end_time,
            )
            if session_id:
                query = query.filter(Activity.session_id == session_id)

            activities = query.order_by(Activity.timestamp).all()

            if not activities:
                logger.info("没有找到活动记录")
                return None

            # 构建活动描述
            activity_descriptions = []
            for act in activities:
                activity_descriptions.append(
                    f"[{format_datetime(act.timestamp)}] {act.activity_type}: {act.description}"
                )

            # 调用AI生成摘要
            result = self.ai_service.generate_summary(
                activities=activity_descriptions,
                start_time=start_time,
                end_time=end_time,
            )

            if not result:
                logger.warning("AI摘要生成失败，使用基本摘要")
                result = {
                    "summary": self._basic_summary(activities),
                    "work_type": "其他",
                    "model": "none",
                    "tokens": 0,
                }

            # 创建日志条目
            entry = JournalEntry(
                session_id=session_id,
                start_time=start_time,
                end_time=end_time,
                work_type=result["work_type"],
                summary=result["summary"],
                ai_model=result.get("model"),
                tokens_used=result.get("tokens", 0),
            )
            db_session.add(entry)
            db_session.flush()
            # 确保属性加载后脱离session
            _ = entry.id, entry.session_id, entry.start_time, entry.end_time
            _ = entry.work_type, entry.summary, entry.ai_model, entry.tokens_used
            db_session.expunge(entry)

            logger.info(f"日志条目已生成: #{entry.id}")
            return entry

    def _basic_summary(self, activities) -> str:
        """生成基本摘要（无AI）"""
        git_commits = [a for a in activities if a.activity_type == "git_commit"]
        file_changes = [a for a in activities if a.activity_type != "git_commit"]

        parts = []
        if git_commits:
            parts.append(f"Git提交 {len(git_commits)} 次")
            for c in git_commits[:5]:
                parts.append(f"  - {c.description}")

        if file_changes:
            parts.append(f"文件变更 {len(file_changes)} 次")

        return "\n".join(parts) if parts else "无活动记录"
