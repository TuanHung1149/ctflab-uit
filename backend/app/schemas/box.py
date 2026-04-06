from pydantic import BaseModel


class ChallengeResponse(BaseModel):
    id: int
    order: int
    title: str
    description: str
    points: int

    model_config = {"from_attributes": True}


class BoxResponse(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    flag_count: int
    is_active: bool

    model_config = {"from_attributes": True}


class BoxDetail(BoxResponse):
    challenges: list[ChallengeResponse]
    port_mappings: dict
