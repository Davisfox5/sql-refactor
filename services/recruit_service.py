from typing import Optional, List, Dict, Any, Tuple
import json
import logging
from datetime import datetime

from models.recruit import Recruit
from .base_service import BaseService
from db.db_utils import execute_query, execute_transaction

class RecruitService(BaseService[Recruit]):
    """Service for Recruit model operations."""
    
    def __init__(self):
        super().__init__(Recruit, 'recruits')
    
    async def get_by_email(self, email: str, user_id: Optional[str] = None) -> Optional[Recruit]:
        """Get a recruit by email address.
        
        Args:
            email: Email address to look up
            user_id: Optional user ID to filter by
            
        Returns:
            Recruit if found, None otherwise
        """
        if user_id:
            query = "SELECT * FROM recruits WHERE email_address = $1 AND user_id = $2"
            results = await execute_query(query, email, user_id)
        else:
            query = "SELECT * FROM recruits WHERE email_address = $1"
            results = await execute_query(query, email)
        
        if not results:
            return None
            
        return Recruit(**results[0])
    
    async def get_by_user(self, user_id: str, limit: int = 100, offset: int = 0) -> List[Recruit]:
        """Get recruits for a specific user.
        
        Args:
            user_id: User ID to filter by
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of Recruit instances
        """
        query = """
            SELECT * FROM recruits 
            WHERE user_id = $1 
            ORDER BY COALESCE(last_name, ''), COALESCE(first_name, '')
            LIMIT $2 OFFSET $3
        """
        results = await execute_query(query, user_id, limit, offset)
        
        return [Recruit(**row) for row in results]
    
    async def search(self, user_id: str, search_term: str, limit: int = 20) -> List[Recruit]:
        """Search for recruits by name or email.
        
        Args:
            user_id: User ID to filter by
            search_term: Term to search for
            limit: Maximum number of records to return
            
        Returns:
            List of matching Recruit instances
        """
        # Create search pattern with wildcards
        pattern = f"%{search_term}%"
        
        query = """
            SELECT * FROM recruits 
            WHERE user_id = $1 
              AND (
                  LOWER(first_name) LIKE LOWER($2) 
                  OR LOWER(last_name) LIKE LOWER($2)
                  OR LOWER(email_address) LIKE LOWER($2)
                  OR LOWER(CONCAT(first_name, ' ', last_name)) LIKE LOWER($2)
              )
            ORDER BY COALESCE(last_name, ''), COALESCE(first_name, '')
            LIMIT $3
        """
        
        results = await execute_query(query, user_id, pattern, limit)
        
        return [Recruit(**row) for row in results]
    
    async def filter_by_grad_year(self, user_id: str, grad_year: str) -> List[Recruit]:
        """Filter recruits by graduation year.
        
        Args:
            user_id: User ID to filter by
            grad_year: Graduation year to filter by
            
        Returns:
            List of matching Recruit instances
        """
        query = """
            SELECT * FROM recruits 
            WHERE user_id = $1 AND grad_year = $2
            ORDER BY COALESCE(last_name, ''), COALESCE(first_name, '')
        """
        
        results = await execute_query(query, user_id, grad_year)
        
        return [Recruit(**row) for row in results]
    
    async def update_evaluation(self, recruit_id: int, rating: str, evaluation: str) -> Optional[Recruit]:
        """Update a recruit's rating and evaluation.
        
        Args:
            recruit_id: Recruit ID to update
            rating: New rating
            evaluation: New evaluation text
            
        Returns:
            Updated Recruit instance or None if not found
        """
        query = """
            UPDATE recruits 
            SET rating = $2, 
                evaluation = $3, 
                last_evaluation_date = $4,
                updated_at = $4
            WHERE id = $1
            RETURNING *
        """
        
        now = datetime.utcnow()
        results = await execute_query(query, recruit_id, rating, evaluation, now)
        
        if not results:
            return None
            
        return Recruit(**results[0])
    
    async def get_recruit_with_schedules(self, recruit_id: int) -> Tuple[Optional[Recruit], List[Dict[str, Any]]]:
        """Get a recruit with their schedules.
        
        Args:
            recruit_id: Recruit ID to look up
            
        Returns:
            Tuple of (Recruit or None, list of schedule dictionaries)
        """
        # First get the recruit
        recruit = await self.get_by_id(recruit_id)
        
        if not recruit:
            return None, []
            
        # Then get their schedules
        schedule_query = """
            SELECT * FROM schedules
            WHERE recruit_id = $1
            ORDER BY date DESC
        """
        
        schedules = await execute_query(schedule_query, recruit_id)
        
        return recruit, schedules
    
    async def get_stats_by_user(self, user_id: str) -> Dict[str, Any]:
        """Get recruit statistics for a user.
        
        Args:
            user_id: User ID to get stats for
            
        Returns:
            Dictionary with recruit statistics
        """
        stats_query = """
            SELECT 
                COUNT(*) as total_recruits,
                COUNT(CASE WHEN rating IS NOT NULL THEN 1 END) as rated_recruits,
                COUNT(DISTINCT grad_year) as distinct_grad_years
            FROM recruits
            WHERE user_id = $1
        """
        
        stats_results = await execute_query(stats_query, user_id)
        
        if not stats_results:
            return {
                "total_recruits": 0,
                "rated_recruits": 0,
                "distinct_grad_years": 0,
                "grad_year_distribution": {}
            }
            
        # Get graduation year distribution
        grad_year_query = """
            SELECT grad_year, COUNT(*) as count
            FROM recruits
            WHERE user_id = $1 AND grad_year IS NOT NULL
            GROUP BY grad_year
            ORDER BY grad_year
        """
        
        grad_year_results = await execute_query(grad_year_query, user_id)
        
        grad_year_distribution = {row['grad_year']: row['count'] for row in grad_year_results}
        
        return {
            **stats_results[0],
            "grad_year_distribution": grad_year_distribution
        }
    
    async def delete_cascade(self, recruit_id: int) -> bool:
        """Delete a recruit and all associated data.
        
        Args:
            recruit_id: ID of recruit to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        # Start a transaction to delete the recruit and related data
        try:
            # First check if the recruit exists
            recruit = await self.get_by_id(recruit_id)
            if not recruit:
                return False
                
            # Define queries for the transaction
            delete_feedback_query = "DELETE FROM extraction_feedback WHERE recruit_id = $1"
            delete_schedules_query = "DELETE FROM schedules WHERE recruit_id = $1"
            delete_recruit_query = "DELETE FROM recruits WHERE id = $1"
            
            # Execute in a transaction
            await execute_transaction([
                (delete_feedback_query, [recruit_id]),
                (delete_schedules_query, [recruit_id]),
                (delete_recruit_query, [recruit_id])
            ])
            
            return True
        except Exception as e:
            self.logger.error(f"Error deleting recruit {recruit_id}: {e}")
            return False
