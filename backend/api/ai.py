"""AI调用API"""

from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.ai_service import get_ai_service
from shared.utils import decrypt_value, encrypt_value

router = APIRouter(prefix="/api/ai", tags=["ai"])
ai_service = get_ai_service()


class TestRequest(BaseModel):
    api_key: str
    base_url: str
    model: str
    endpoint: str = "/v1/chat/completions"


class SummarizeRequest(BaseModel):
    activities: list[str]
    start_time: str
    end_time: str


class ClassifyRequest(BaseModel):
    description: str


@router.post("/test")
def test_connection(data: TestRequest):
    """测试API连接"""
    config = {
        "api_key": data.api_key,
        "base_url": data.base_url,
        "model": data.model,
        "endpoint": data.endpoint,
    }
    return ai_service.test_connection(config)


@router.post("/summarize")
def summarize(data: SummarizeRequest):
    """生成摘要"""
    from datetime import datetime

    start = datetime.fromisoformat(data.start_time)
    end = datetime.fromisoformat(data.end_time)

    result = ai_service.generate_summary(
        activities=data.activities,
        start_time=start,
        end_time=end,
    )

    if result:
        return {"success": True, **result}
    return {"success": False, "message": "摘要生成失败"}


@router.post("/classify")
def classify(data: ClassifyRequest):
    """分类工作类型"""
    work_type = ai_service.classify_work_type(data.description)
    return {"work_type": work_type}
