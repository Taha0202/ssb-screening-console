from typing import Optional
from pydantic import BaseModel, ConfigDict

class LoginRequest(BaseModel):
    badge_id: str
    password: str

class UserResponse(BaseModel):
    id: str
    badge_id: str
    full_name: str
    role: str
    checkpoint_id: Optional[str] = None
    checkpoint_location: Optional[str] = "Raxaul Checkpoint"
    status: Optional[str] = "ACTIVE"

    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
