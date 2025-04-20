from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum, auto
from pydantic import Field, validator

from .base import TimestampModel

class Email(TimestampModel):
    """Email model corresponding to the emails table."""
    id: Optional[int] = None
    user_id: str
    recruit_email: Optional[str] = None
    email_id: str  # Unique identifier from email provider
    date: Optional[str] = None
    subject: Optional[str] = None
    summary: Optional[str] = None
    highlights: Optional[str] = None
    profile: Optional[str] = None
    schedule: Optional[str] = None
    folder_id: Optional[str] = None
    sender: Optional[str] = None
    received_date: Optional[datetime] = None
    is_read: Optional[int] = 0
    has_attachments: Optional[int] = 0
    body: Optional[str] = None
    import_date: Optional[datetime] = None
    processed: Optional[int] = 0
    processed_date: Optional[datetime] = None
    
    class Config:
        from_attributes = True
    
    def __repr__(self) -> str:
        """String representation of the Email."""
        return f"Email(id={self.id}, user_id={self.user_id}, subject={self.subject})"

class ProcessingStatus(str, Enum):
    """Processing status enum for email queue."""
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class EmailQueue(TimestampModel):
    """EmailQueue model corresponding to the email_queue table."""
    id: Optional[int] = None
    user_id: str
    email_id: str  # References Email.email_id, not Email.id
    provider: str
    folder_id: str
    status: ProcessingStatus = ProcessingStatus.QUEUED
    priority: int = 0
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True
    
    def __repr__(self) -> str:
        """String representation of the EmailQueue."""
        return f"EmailQueue(id={self.id}, user_id={self.user_id}, status={self.status})"
