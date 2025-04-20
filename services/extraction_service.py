from typing import Optional, List, Dict, Any, Tuple
import json
import logging
from datetime import datetime

from models.feedback import ExtractionFeedback, ExtractionPattern
from .base_service import BaseService
from db.db_utils import execute_query, execute_transaction

class ExtractionService(BaseService[ExtractionFeedback]):
    """Service for ExtractionFeedback model operations."""
    
    def __init__(self):
        super().__init__(ExtractionFeedback, 'extraction_feedback')
        self.pattern_service = ExtractionPatternService()
    
    async def get_by_email(self, email_id: str) -> List[ExtractionFeedback]:
        """Get all feedback for an email.
        
        Args:
            email_id: Email ID to get feedback for
            
        Returns:
            List of ExtractionFeedback instances
        """
        query = """
            SELECT * FROM extraction_feedback
            WHERE email_id = $1
            ORDER BY created_at DESC
        """
        
        results = await execute_query(query, email_id)
        
        return [ExtractionFeedback(**row) for row in results]
    
    async def get_by_recruit(self, recruit_id: int) -> List[ExtractionFeedback]:
        """Get all feedback for a recruit.
        
        Args:
            recruit_id: Recruit ID to get feedback for
            
        Returns:
            List of ExtractionFeedback instances
        """
        query = """
            SELECT * FROM extraction_feedback
            WHERE recruit_id = $1
            ORDER BY created_at DESC
        """
        
        results = await execute_query(query, recruit_id)
        
        return [ExtractionFeedback(**row) for row in results]
    
    async def get_by_user(self, user_id: str, limit: int = 20) -> List[ExtractionFeedback]:
        """Get all feedback by a user.
        
        Args:
            user_id: User ID to get feedback for
            limit: Maximum number of records to return
            
        Returns:
            List of ExtractionFeedback instances
        """
        query = """
            SELECT * FROM extraction_feedback
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
        """
        
        results = await execute_query(query, user_id, limit)
        
        return [ExtractionFeedback(**row) for row in results]
    
    async def create_feedback(self, user_id: str, email_id: str, recruit_id: int, 
                             original_text: str, original_extraction: Dict[str, Any],
                             corrected_values: Dict[str, Any], model_used: Optional[str] = None,
                             notes: Optional[str] = None, used_cache: bool = False) -> ExtractionFeedback:
        """Create a new extraction feedback entry.
        
        Args:
            user_id: User ID creating the feedback
            email_id: Email ID the feedback is for
            recruit_id: Recruit ID the feedback is for
            original_text: Original text that was processed
            original_extraction: Original extraction results
            corrected_values: Corrected values
            model_used: Optional name of the model used for extraction
            notes: Optional notes about the extraction
            used_cache: Whether the extraction used cached results
            
        Returns:
            Created ExtractionFeedback instance
        """
        # Create the feedback model
        feedback = ExtractionFeedback(
            user_id=user_id,
            email_id=email_id,
            recruit_id=recruit_id,
            original_text=original_text,
            original_extraction=original_extraction,
            corrected_values=corrected_values,
            model_used=model_used,
            notes=notes,
            used_cache=used_cache
        )
        
        # Save to database
        return await self.create(feedback)
    
    async def get_feedback_with_recruit(self, feedback_id: int) -> Tuple[Optional[ExtractionFeedback], Optional[Dict[str, Any]]]:
        """Get feedback with recruit information.
        
        Args:
            feedback_id: Feedback ID to look up
            
        Returns:
            Tuple of (ExtractionFeedback or None, recruit dictionary or None)
        """
        query = """
            SELECT ef.*, 
                   r.id as recruit_id, r.first_name, r.last_name, 
                   r.email_address, r.grad_year
            FROM extraction_feedback ef
            JOIN recruits r ON ef.recruit_id = r.id
            WHERE ef.id = $1
        """
        
        results = await execute_query(query, feedback_id)
        
        if not results:
            return None, None
            
        feedback_data = results[0]
        
        # Extract recruit data
        recruit_data = {
            'id': feedback_data.pop('recruit_id'),
            'first_name': feedback_data.pop('first_name'),
            'last_name': feedback_data.pop('last_name'),
            'email_address': feedback_data.pop('email_address'),
            'grad_year': feedback_data.pop('grad_year')
        }
        
        # Convert JSON fields if they're in string format
        for field in ['original_extraction', 'corrected_values']:
            if isinstance(feedback_data[field], str):
                feedback_data[field] = json.loads(feedback_data[field])
        
        feedback = ExtractionFeedback(**feedback_data)
        
        return feedback, recruit_data
    
    async def get_stats_by_user(self, user_id: str) -> Dict[str, Any]:
        """Get extraction feedback statistics for a user.
        
        Args:
            user_id: User ID to get stats for
            
        Returns:
            Dictionary with feedback statistics
        """
        stats_query = """
            SELECT 
                COUNT(*) as total_feedback,
                COUNT(DISTINCT email_id) as distinct_emails,
                COUNT(DISTINCT recruit_id) as distinct_recruits,
                COUNT(CASE WHEN used_cache = TRUE THEN 1 END) as cached_extractions
            FROM extraction_feedback
            WHERE user_id = $1
        """
        
        stats_results = await execute_query(stats_query, user_id)
        
        if not stats_results:
            return {
                "total_feedback": 0,
                "distinct_emails": 0,
                "distinct_recruits": 0,
                "cached_extractions": 0,
                "model_distribution": {}
            }
            
        # Get model distribution
        model_query = """
            SELECT model_used, COUNT(*) as count
            FROM extraction_feedback
            WHERE user_id = $1 AND model_used IS NOT NULL
            GROUP BY model_used
        """
        
        model_results = await execute_query(model_query, user_id)
        
        model_distribution = {row['model_used']: row['count'] for row in model_results}
        
        return {
            **stats_results[0],
            "model_distribution": model_distribution
        }


class ExtractionPatternService(BaseService[ExtractionPattern]):
    """Service for ExtractionPattern model operations."""
    
    def __init__(self):
        super().__init__(ExtractionPattern, 'extraction_patterns')
    
    async def get_active_patterns(self) -> List[ExtractionPattern]:
        """Get all active extraction patterns.
        
        Returns:
            List of active ExtractionPattern instances
        """
        query = """
            SELECT * FROM extraction_patterns
            WHERE is_active = TRUE
            ORDER BY priority DESC, field_name
        """
        
        results = await execute_query(query)
        
        return [ExtractionPattern(**row) for row in results]
    
    async def get_by_field(self, field_name: str) -> List[ExtractionPattern]:
        """Get all patterns for a specific field.
        
        Args:
            field_name: Field name to get patterns for
            
        Returns:
            List of ExtractionPattern instances for the field
        """
        query = """
            SELECT * FROM extraction_patterns
            WHERE field_name = $1
            ORDER BY priority DESC
        """
        
        results = await execute_query(query, field_name)
        
        return [ExtractionPattern(**row) for row in results]
    
    async def create_pattern(self, field_name: str, pattern: str, 
                            description: Optional[str] = None, 
                            priority: int = 0, is_active: bool = True) -> ExtractionPattern:
        """Create a new extraction pattern.
        
        Args:
            field_name: Field name the pattern is for
            pattern: The pattern string (regex or other format)
            description: Optional description of the pattern
            priority: Priority of the pattern (higher = higher priority)
            is_active: Whether the pattern is active
            
        Returns:
            Created ExtractionPattern instance
        """
        # Create the pattern model
        pattern_model = ExtractionPattern(
            field_name=field_name,
            pattern=pattern,
            description=description,
            priority=priority,
            is_active=is_active
        )
        
        # Save to database
        return await self.create(pattern_model)
    
    async def toggle_active(self, pattern_id: int, is_active: bool) -> Optional[ExtractionPattern]:
        """Toggle the active status of a pattern.
        
        Args:
            pattern_id: Pattern ID to update
            is_active: New active status
            
        Returns:
            Updated ExtractionPattern if successful, None if not found
        """
        query = """
            UPDATE extraction_patterns
            SET is_active = $2, updated_at = $3
            WHERE id = $1
            RETURNING *
        """
        
        now = datetime.utcnow()
        results = await execute_query(query, pattern_id, is_active, now)
        
        if not results:
            return None
            
        return ExtractionPattern(**results[0])
