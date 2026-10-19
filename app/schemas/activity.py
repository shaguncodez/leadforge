from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.activity import ActivityType


class ActivityBase(BaseModel):
    type: ActivityType
    notes: str = Field(..., min_length=1)


class ActivityCreate(ActivityBase):
    pass


class ActivityResponse(ActivityBase):
    id: str
    lead_id: str
    actor_id: Optional[str] = None
    created_at: datetime
    actor_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
