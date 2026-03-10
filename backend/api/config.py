"""API配置管理API"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database import get_db_session
from backend.models.api_config import ApiConfig
from backend.services.ai_service import get_ai_service
from shared.config import get_config, _deep_copy_dict
from shared.utils import decrypt_value, encrypt_value

router = APIRouter(prefix="/api/config", tags=["config"])
ai_service = get_ai_service()

# 密码脱敏占位符
PASSWORD_MASK = "******"

# 各 section 中需要脱敏的字段
SENSITIVE_FIELDS = {
    "database": ["password"],
    "ssh": ["password"],
}


class ApiConfigCreate(BaseModel):
    name: str
    api_key: str
    base_url: str
    model: str
    endpoint: str = "/v1/chat/completions"


class ApiConfigUpdate(BaseModel):
    name: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    endpoint: str | None = None
    is_active: bool | None = None


class ApiConfigResponse(BaseModel):
    id: int
    name: str
    base_url: str
    model: str
    endpoint: str
    is_active: bool
    test_status: str | None
    test_message: str | None

    class Config:
        from_attributes = True


@router.get("/api")
def list_api_configs():
    """获取所有API配置"""
    with get_db_session() as session:
        configs = session.query(ApiConfig).all()
        return [
            {
                "id": c.id,
                "name": c.name,
                "base_url": c.base_url,
                "model": c.model,
                "endpoint": c.endpoint,
                "is_active": c.is_active,
                "test_status": c.test_status,
                "test_message": c.test_message,
            }
            for c in configs
        ]


@router.post("/api")
def create_api_config(data: ApiConfigCreate):
    """创建API配置"""
    with get_db_session() as session:
        # 检查名称是否已存在
        existing = session.query(ApiConfig).filter(ApiConfig.name == data.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="配置名称已存在")

        config = ApiConfig(
            name=data.name,
            api_key=encrypt_value(data.api_key),
            base_url=data.base_url,
            model=data.model,
            endpoint=data.endpoint,
            is_active=False,
        )
        session.add(config)
        session.flush()
        return {"id": config.id, "message": "API配置已创建"}


@router.put("/api/{config_id}")
def update_api_config(config_id: int, data: ApiConfigUpdate):
    """更新API配置"""
    with get_db_session() as session:
        config = session.query(ApiConfig).get(config_id)
        if not config:
            raise HTTPException(status_code=404, detail="配置不存在")

        if data.name:
            config.name = data.name
        if data.api_key:
            config.api_key = encrypt_value(data.api_key)
        if data.base_url:
            config.base_url = data.base_url
        if data.model:
            config.model = data.model
        if data.endpoint:
            config.endpoint = data.endpoint
        if data.is_active is not None:
            # 如果设置为活跃，取消其他配置的活跃状态
            if data.is_active:
                session.query(ApiConfig).update({"is_active": False})
            config.is_active = data.is_active

        return {"message": "API配置已更新"}


@router.delete("/api/{config_id}")
def delete_api_config(config_id: int):
    """删除API配置"""
    with get_db_session() as session:
        config = session.query(ApiConfig).get(config_id)
        if not config:
            raise HTTPException(status_code=404, detail="配置不存在")
        session.delete(config)
        return {"message": "API配置已删除"}


@router.post("/api/{config_id}/test")
def test_api_config(config_id: int):
    """测试API配置"""
    with get_db_session() as session:
        config = session.query(ApiConfig).get(config_id)
        if not config:
            raise HTTPException(status_code=404, detail="配置不存在")

        api_config = {
            "id": config.id,
            "api_key": decrypt_value(config.api_key),
            "base_url": config.base_url,
            "model": config.model,
            "endpoint": config.endpoint,
        }

        result = ai_service.test_connection(api_config)

        # 更新测试状态
        config.test_status = "success" if result["success"] else "failed"
        config.test_message = result.get("message", "")

        return result


@router.get("/app")
def get_app_config():
    """获取完整应用配置（密码字段脱敏）"""
    config = get_config()
    config.load()
    cfg = config.to_dict()

    # 脱敏敏感字段
    for section, fields in SENSITIVE_FIELDS.items():
        if section in cfg:
            for field in fields:
                if field in cfg[section] and cfg[section][field]:
                    cfg[section][field] = PASSWORD_MASK

    return cfg


@router.put("/app/{section}")
def update_app_config_section(section: str, data: dict):
    """更新指定 section 的应用配置"""
    valid_sections = ["database", "ssh", "tracker", "ai", "web"]
    if section not in valid_sections:
        raise HTTPException(status_code=400, detail=f"无效的配置段: {section}，可选: {', '.join(valid_sections)}")

    config = get_config()
    config.load()

    current = config.to_dict()
    if section not in current:
        raise HTTPException(status_code=400, detail=f"配置段不存在: {section}")

    # 合并数据，密码字段如果是占位符或空字符串则保留原值
    sensitive = SENSITIVE_FIELDS.get(section, [])
    for key, value in data.items():
        if key in sensitive and value in (PASSWORD_MASK, ""):
            continue
        current[section][key] = value

    config._config = current
    config.save()
    config.load()

    return {"message": f"配置段 {section} 已更新"}
