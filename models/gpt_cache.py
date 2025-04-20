from datetime import datetime
from typing import Optional, Dict, Any, List
import json
from pydantic import Field, validator

from .base import TimestampModel

class GPTCache(TimestampModel):
    """GPTCache model corresponding to the gpt_cache table."""
    id: Optional[int] = None
    content_hash: str  # Not nullable, unique, indexed
    email: Optional[str] = None  # Nullable, indexed
    result_json: Dict[str, Any]  # JSON stored as Text
    
    class Config:
        from_attributes = True
    
    @validator('result_json', pre=True)
    def validate_result_json(cls, v):
        """Validate and convert result_json from JSON string."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON format for result_json")
        return v
    
    def __repr__(self) -> str:
        """String representation of the GPTCache."""
        return f"GPTCache(id={self.id}, content_hash={self.content_hash}, email={self.email})"
