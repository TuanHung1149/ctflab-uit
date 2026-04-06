from datetime import datetime

from pydantic import BaseModel


class InstanceCreate(BaseModel):
    box_slug: str


class InstanceResponse(BaseModel):
    id: int
    box_id: int
    status: str
    container_ip: str | None
    started_at: datetime | None
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class VpnConfigResponse(BaseModel):
    config_text: str
    filename: str
