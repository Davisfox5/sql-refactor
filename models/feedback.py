from datetime import datetime
from typing import Optional, Dict, Any, List, Union
import json
from pydantic import Field, validator

from .base import TimestampModel

class ExtractionFeedback(TimestampModel):
    """ExtractionFeedback model corresponding to the extraction_feedback table."""
    id: Optional[int] = None
    user_id: str
    email_id: str
    recruit_id: int
    original_text: Optional[str] = None
    original_extraction: Dict[str, Any]  # JSON field
    corrected_values: Dict[str, Any]  # JSON field
    notes: Optional[str] = None
    used_cache: bool = False
    model_used: Optional[str] = None
    
    class Config:
        from_attributes = True
    
    @validator('original_extraction', 'corrected_values', pre=True)
    def validate_json_fields(cls, v):
        """Validate and convert JSON fields."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON format")
        return v
    
    def __repr__(self) -> str:
        """String representation of the ExtractionFeedback."""
        return f"ExtractionFeedback(id={self.id}, user_id={self.user_id}, recruit_id={self.recruit_id})"

class ExtractionPattern(TimestampModel):
    """ExtractionPattern model corresponding to the extraction_patterns table."""
    id: Optional[int] = None
    field_name: str
    pattern: str
    description: Optional[str] = None
    priority: int = 0
    is_active: bool = True
    
    class Config:
        from_attributes = True
    
    def __repr__(self) -> str:
        """String representation of the ExtractionPattern."""
        return f"ExtractionPattern(id={self.id}, field_name={self.field_name})"
