from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class CheckpointBase(BaseModel):
    checkpoint_code: str
    name: str
    location: str
    state: str
    district: str
    status: str = "ACTIVE"

class CheckpointCreate(CheckpointBase):
    pass

class CheckpointUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    status: Optional[str] = None

class CheckpointResponse(CheckpointBase):
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
