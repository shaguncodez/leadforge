from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.task import TaskStatus


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    due_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.pending
    assignee_id: Optional[str] = None


class TaskCreate(TaskBase):
    lead_id: str


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    due_at: Optional[datetime] = None
    status: Optional[TaskStatus] = None
    assignee_id: Optional[str] = None


class TaskResponse(TaskBase):
    id: str
    lead_id: str
    created_at: datetime
    updated_at: datetime
    lead_name: Optional[str] = None
    assignee_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
