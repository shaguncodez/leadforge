from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.lead import LeadSource, LeadStatus


class LeadBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    company: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    source: LeadSource = LeadSource.web_form
    status: LeadStatus = LeadStatus.new
    notes: Optional[str] = None


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    company: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    source: Optional[LeadSource] = None
    status: Optional[LeadStatus] = None
    notes: Optional[str] = None
    owner_id: Optional[str] = None


class LeadResponse(LeadBase):
    id: str
    owner_id: str
    score: int
    created_at: datetime
    updated_at: datetime
    owner_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LeadListResponse(BaseModel):
    items: List[LeadResponse]
    total: int
    page: int
    per_page: int
    pages: int


class ScoreBreakdown(BaseModel):
    purchase_intent: int = Field(..., description="Score from lead status (max 35)")
    engagement: int = Field(..., description="Score from activity count (max 25)")
    profile_completeness: int = Field(..., description="Score from contact info completeness (max 20)")
    recency: int = Field(..., description="Score from recent activity in last 7 days (max 20)")
    total: int = Field(..., description="Total combined score (0-100)")


class LeadScoreResponse(BaseModel):
    lead_id: str
    score: int
    breakdown: ScoreBreakdown
    explanation: Dict[str, Any]
