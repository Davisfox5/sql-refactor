from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import Field, validator

from .base import TimestampModel

class Team(TimestampModel):
    """Team model corresponding to the teams table."""
    id: Optional[int] = None
    name: str  # Not nullable, unique
    normalized_name: str  # Not nullable
    birth_year: Optional[str] = None
    gender: Optional[str] = None
    age_group: Optional[str] = None
    
    class Config:
        from_attributes = True
    
    @validator('normalized_name', pre=True, always=True)
    def set_normalized_name(cls, v, values):
        """Normalize the team name if not provided."""
        if not v and 'name' in values and values['name']:
            # Basic normalization logic - replace with actual logic used in the app
            return values['name'].lower().replace(' ', '_')
        return v
    
    def __repr__(self) -> str:
        """String representation of the Team."""
        return f"Team(id={self.id}, name={self.name})"

class TeamAlias(TimestampModel):
    """TeamAlias model corresponding to the team_aliases table."""
    id: Optional[int] = None
    team_id: int  # ForeignKey to Team.id
    alias: str  # Not nullable, unique
    source: Optional[str] = None
    
    class Config:
        from_attributes = True
    
    def __repr__(self) -> str:
        """String representation of the TeamAlias."""
        return f"TeamAlias(id={self.id}, team_id={self.team_id}, alias={self.alias})"
