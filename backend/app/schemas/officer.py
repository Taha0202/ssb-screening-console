from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class OfficerBase(BaseModel):
    badge_id: str
    full_name: str
    role: str = "OFFICER"  # 'OFFICER', 'SUPERVISOR', 'ANALYST', 'ADMIN'
    checkpoint_id: Optional[str] = None
    checkpoint_location: Optional[str] = None
    status: str = "ACTIVE"

class OfficerCreate(OfficerBase):
    password: str

class OfficerUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    checkpoint_id: Optional[str] = None
    checkpoint_location: Optional[str] = None
    status: Optional[str] = None
    password: Optional[str] = None

class OfficerResponse(OfficerBase):
    id: str
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
