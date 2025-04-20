from datetime import datetime
from typing import Dict, Any, Optional, TypeVar, Generic, Type
from pydantic import BaseModel, Field, ConfigDict

# Type variable for use with generic methods
T = TypeVar('T', bound='BaseModel')

class TimestampModel(BaseModel):
    """Base model with timestamp fields."""
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
        extra='ignore'
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return self.model_dump(exclude_none=True)
    
    def __repr__(self) -> str:
        """String representation of the model."""
        class_name = self.__class__.__name__
        attrs = []
        for attr, value in self.__dict__.items():
            if not attr.startswith('_'):
                attrs.append(f"{attr}={value!r}")
        return f"{class_name}({', '.join(attrs)})"
