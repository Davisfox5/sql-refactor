from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid
from pydantic import BaseModel, Field, EmailStr, validator

from .base import TimestampModel

class User(TimestampModel):
    """User model corresponding to the users table."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    hashed_password: Optional[str] = None
    provider: Optional[str] = None
    oauth_access_token: Optional[str] = None
    oauth_refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    is_new_user: int = 1
    is_admin: bool = False
    has_consented: bool = False
    has_completed_setup: bool = False
    name: Optional[str] = None
    organization: Optional[str] = None
    
    class Config:
        from_attributes = True
    
    @validator('email')
    def email_must_be_valid(cls, v):
        """Validate that email is properly formatted."""
        # EmailStr already validates format, this is just an example
        return v

class UserSettings(BaseModel):
    """UserSettings model corresponding to the user_settings table."""
    user_id: str
    selected_folders: Optional[str] = None
    fetch_frequency: str = 'manual'
    batch_process_enabled: bool = False
    
    class Config:
        from_attributes = True
    
    def __repr__(self) -> str:
        """String representation of the UserSettings."""
        return f"UserSettings(user_id={self.user_id!r}, fetch_frequency={self.fetch_frequency!r})"
