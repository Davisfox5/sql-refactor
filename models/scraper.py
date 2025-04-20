from datetime import datetime
from typing import Optional, Dict, Any, List, Union
import json
from pydantic import Field, validator

from .base import TimestampModel

class ScraperConfiguration(TimestampModel):
    """ScraperConfiguration model corresponding to the scraper_configurations table."""
    id: Optional[int] = None
    name: str
    source: str
    active: bool = True
    parameters: Optional[Dict[str, Any]] = None  # JSON stored as Text
    
    class Config:
        from_attributes = True
    
    @validator('parameters', pre=True)
    def validate_parameters(cls, v):
        """Validate and convert parameters from JSON string."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON format for parameters")
        return v or {}
    
    def __repr__(self) -> str:
        """String representation of the ScraperConfiguration."""
        return f"ScraperConfiguration(id={self.id}, name={self.name}, source={self.source})"

class ScrapingLog(TimestampModel):
    """ScrapingLog model corresponding to the scraping_logs table."""
    id: Optional[int] = None
    config_id: int  # ForeignKey to ScraperConfiguration.id
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    total_matches: int = 0
    new_matches: int = 0
    results: Optional[Dict[str, Any]] = None  # JSON stored as Text
    error: Optional[str] = None
    
    class Config:
        from_attributes = True
    
    @validator('results', pre=True)
    def validate_results(cls, v):
        """Validate and convert results from JSON string."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON format for results")
        return v or {}
    
    def __repr__(self) -> str:
        """String representation of the ScrapingLog."""
        return f"ScrapingLog(id={self.id}, config_id={self.config_id}, total_matches={self.total_matches})"
