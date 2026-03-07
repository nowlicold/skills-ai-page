"""允许前端或用户手动保存配置（仅白名单 key），写入 backend/.env"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.services.config_store import ALLOWED_KEYS, set_config

router = APIRouter()


class ConfigSetRequest(BaseModel):
    key: str
    value: str


class ConfigSetResponse(BaseModel):
    ok: bool
    message: str


@router.post("/config", response_model=ConfigSetResponse)
def set_config_api(req: ConfigSetRequest):
    """保存一项配置到本地 .env（仅支持白名单内的 key，如 FELO_API_KEY）。"""
    ok, message = set_config(req.key, req.value)
    return ConfigSetResponse(ok=ok, message=message)


@router.get("/config/keys")
def list_allowed_config_keys():
    """返回允许通过对话或 API 设置的配置项名称列表。"""
    return {"keys": list(sorted(ALLOWED_KEYS))}
