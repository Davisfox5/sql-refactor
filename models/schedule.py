from datetime import datetime
from typing import Optional, Dict, Any, List
import json
from pydantic import Field, validator

from .base import TimestampModel

class Schedule(TimestampModel):
    """Schedule model corresponding to the schedules table."""
    id: Optional[int] = None
    user_id: str
    recruit_id: Optional[int] = None
    recruit_email: Optional[str] = None  # legacy field
    home_team: Optional[str] = None
    away_team: Optional[str] = None
    home_participants: Optional[str] = None  # JSON array as text
    away_participants: Optional[str] = None  # JSON array as text
    event_name: Optional[str] = None
    is_master: bool = False
    source: str = 'manual'
    date: str  # Not nullable
    time: Optional[str] = None
    location: Optional[str] = None
    
    class Config:
        from_attributes = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with additional processing for JSON fields."""
        result = super().to_dict()
        
        # Process JSON fields stored as text
        if self.home_participants:
            try:
                result['home_participants'] = json.loads(self.home_participants)
            except:
                pass
                
        if self.away_participants:
            try:
                result['away_participants'] = json.loads(self.away_participants)
            except:
                pass
                
        # Add formatted datetime
        try:
            if self.date:
                date_str = self.date
                time_str = self.time or "00:00"
                
                # Handle various date formats
                if 'T' in date_str:
                    # ISO format
                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    # Try common formats
                    formats = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]
                    for fmt in formats:
                        try:
                            dt = datetime.strptime(f"{date_str} {time_str}", f"{fmt} %H:%M")
                            break
                        except:
                            continue
                    else:
                        dt = None
                
                if dt:
                    result['formatted_datetime'] = dt.isoformat()
        except:
            pass
            
        return result
