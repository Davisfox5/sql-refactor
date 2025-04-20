from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import Field, validator

from .base import TimestampModel

class Recruit(TimestampModel):
    """Recruit model corresponding to the recruits table."""
    id: Optional[int] = None
    user_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email_address: Optional[str] = None
    phone: Optional[str] = None
    grad_year: Optional[str] = None
    state: Optional[str] = None
    gpa: Optional[str] = None
    majors: Optional[str] = None
    positions: Optional[str] = None
    clubs: Optional[str] = None
    coach_name: Optional[str] = None
    coach_phone: Optional[str] = None
    coach_email: Optional[str] = None
    rating: Optional[str] = None
    evaluation: Optional[str] = None
    last_evaluation_date: Optional[datetime] = None
    
    class Config:
        from_attributes = True
    
    @validator('email_address')
    def validate_email(cls, v):
        """Basic email validation."""
        if v is not None and '@' not in v:
            raise ValueError('Invalid email format')
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with additional processing."""
        result = super().to_dict()
        
        # Convert any specific fields as needed
        if self.majors:
            try:
                # Handle JSON stored as string if needed
                if isinstance(self.majors, str) and self.majors.startswith('['):
                    import json
                    result['majors'] = json.loads(self.majors)
            except:
                pass
                
        if self.positions:
            try:
                if isinstance(self.positions, str) and self.positions.startswith('['):
                    import json
                    result['positions'] = json.loads(self.positions)
            except:
                pass
                
        if self.clubs:
            try:
                if isinstance(self.clubs, str) and self.clubs.startswith('['):
                    import json
                    result['clubs'] = json.loads(self.clubs)
            except:
                pass
                
        return result
