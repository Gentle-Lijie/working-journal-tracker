"""AI调用服务"""

import logging
from datetime import datetime
from typing import Optional

import httpx

from backend.database import get_db_session
from backend.models.api_config import ApiConfig
from backend.models.token_usage import TokenUsage
from shared.config import get_config
from shared.utils import decrypt_value

logger = logging.getLogger(__name__)

# 摘要生成Prompt模板
SUMMARY_PROMPT = """你是一个工作日志助手。请根据以下工作活动记录，生成一份简洁的中文工作摘要。

时间范围：{start_time} 至 {end_time}

活动记录：
{activities}

请按以下格式输出：
1. **工作类型**：从以下类型中选择最匹配的一个：开发、会议、调研、测试、文档、其他
2. **工作摘要**：用2-3句话概括这段时间的主要工作内容
3. **关键产出**：列出主要的成果（如提交的功能、修复的bug等）

请直接输出内容，不需要额外的格式标记。"""

# 分类Prompt
CLASSIFY_PROMPT = """请根据以下工作活动描述，判断工作类型。只返回一个类型名称。

可选类型：开发、会议、调研、测试、文档、其他

活动描述：
{description}

工作类型："""


class AIService:
    """AI服务"""

    def __init__(self):
        self._config = get_config()
        self._client = None
        self._api_config = None

    def _get_active_config(self) -> Optional[dict]:
        """获取活跃的API配置"""
        try:
            with get_db_session() as session:
                config = session.query(ApiConfig).filter(ApiConfig.is_active == True).first()
                if config:
                    return {
                        "id": config.id,
                        "name": config.name,
                        "api_key": decrypt_value(config.api_key),
                        "base_url": config.base_url,
                        "model": config.model,
                        "endpoint": config.endpoint or "/v1/chat/completions",
                    }
        except Exception as e:
            logger.error(f"获取API配置失败: {e}")
        return None

    def _make_request(self, messages: list[dict], api_config: dict | None = None) -> dict:
        """调用AI API"""
        config = api_config or self._get_active_config()
        if not config:
            raise ValueError("没有可用的API配置，请在Web面板中配置API")

        url = f"{config['base_url'].rstrip('/')}{config['endpoint']}"
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": config["model"],
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 1000,
        }

        timeout = self._config.get("ai", "timeout", default=30)

        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()

    def generate_summary(
        self,
        activities: list[str],
        start_time: datetime,
        end_time: datetime,
        api_config: dict | None = None,
    ) -> dict | None:
        """生成工作摘要"""
        prompt = SUMMARY_PROMPT.format(
            start_time=start_time.strftime("%Y-%m-%d %H:%M"),
            end_time=end_time.strftime("%Y-%m-%d %H:%M"),
            activities="\n".join(activities),
        )

        messages = [
            {"role": "system", "content": "你是一个专业的工作日志助手，擅长总结和分类工作内容。"},
            {"role": "user", "content": prompt},
        ]

        try:
            result = self._make_request(messages, api_config)
            content = result["choices"][0]["message"]["content"]

            # 记录Token使用
            usage = result.get("usage", {})
            self._record_token_usage(
                api_config_id=api_config.get("id") if api_config else None,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )

            # 解析工作类型
            work_type = "其他"
            for wt in ["开发", "会议", "调研", "测试", "文档"]:
                if wt in content[:50]:
                    work_type = wt
                    break

            return {
                "summary": content,
                "work_type": work_type,
                "model": result.get("model", "unknown"),
                "tokens": usage.get("total_tokens", 0),
            }

        except Exception as e:
            logger.error(f"AI摘要生成失败: {e}")
            return None

    def classify_work_type(self, description: str) -> str:
        """分类工作类型"""
        prompt = CLASSIFY_PROMPT.format(description=description)
        messages = [{"role": "user", "content": prompt}]

        try:
            result = self._make_request(messages)
            content = result["choices"][0]["message"]["content"].strip()
            # 提取类型
            for wt in ["开发", "会议", "调研", "测试", "文档", "其他"]:
                if wt in content:
                    return wt
            return "其他"
        except Exception as e:
            logger.error(f"工作类型分类失败: {e}")
            return "其他"

    def test_connection(self, api_config: dict) -> dict:
        """测试API连接"""
        messages = [{"role": "user", "content": "Hello, respond with 'OK' only."}]

        try:
            import time

            start = time.time()
            result = self._make_request(messages, api_config)
            elapsed = time.time() - start

            return {
                "success": True,
                "response_time": round(elapsed * 1000),
                "model": result.get("model", "unknown"),
                "message": "连接成功",
            }
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "message": f"HTTP错误: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e),
            }

    def _record_token_usage(
        self,
        api_config_id: int | None = None,
        journal_entry_id: int | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
    ):
        """记录Token使用"""
        try:
            with get_db_session() as session:
                usage = TokenUsage(
                    api_config_id=api_config_id,
                    journal_entry_id=journal_entry_id,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                )
                session.add(usage)
        except Exception as e:
            logger.error(f"记录Token使用失败: {e}")


# 全局AI服务实例
_ai_service: AIService | None = None


def get_ai_service() -> AIService:
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
