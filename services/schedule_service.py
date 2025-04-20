from typing import Optional, List, Dict, Any, Tuple
import json
import logging
from datetime import datetime, timedelta

from models.schedule import Schedule
from .base_service import BaseService
from db.db_utils import execute_query, execute_transaction

class ScheduleService(BaseService[Schedule]):
    """Service for Schedule model operations."""
    
    def __init__(self):
        super().__init__(Schedule, 'schedules')
    
    async def get_by_user(self, user_id: str, limit: int = 100, offset: int = 0) -> List[Schedule]:
        """Get schedules for a specific user.
        
        Args:
            user_id: User ID to filter by
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of Schedule instances
        """
        query = """
            SELECT * FROM schedules 
            WHERE user_id = $1 
            ORDER BY date DESC
            LIMIT $2 OFFSET $3
        """
        results = await execute_query(query, user_id, limit, offset)
        
        return [Schedule(**row) for row in results]
    
    async def get_by_recruit(self, recruit_id: int, limit: int = 100, offset: int = 0) -> List[Schedule]:
        """Get schedules for a specific recruit.
        
        Args:
            recruit_id: Recruit ID to filter by
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of Schedule instances
        """
        query = """
            SELECT * FROM schedules 
            WHERE recruit_id = $1 
            ORDER BY date DESC
            LIMIT $2 OFFSET $3
        """
        results = await execute_query(query, recruit_id, limit, offset)
        
        return [Schedule(**row) for row in results]
    
    async def get_upcoming_schedules(self, user_id: str, days: int = 30) -> List[Schedule]:
        """Get upcoming schedules for a user within the next X days.
        
        Args:
            user_id: User ID to filter by
            days: Number of days to look ahead
            
        Returns:
            List of upcoming Schedule instances
        """
        # Calculate the date range
        today = datetime.now().strftime('%Y-%m-%d')
        end_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
        
        query = """
            SELECT * FROM schedules 
            WHERE user_id = $1 
              AND date >= $2 
              AND date <= $3
            ORDER BY date ASC
        """
        results = await execute_query(query, user_id, today, end_date)
        
        return [Schedule(**row) for row in results]
    
    async def get_schedules_by_date_range(self, user_id: str, start_date: str, end_date: str) -> List[Schedule]:
        """Get schedules for a user within a date range.
        
        Args:
            user_id: User ID to filter by
            start_date: Start date string (YYYY-MM-DD)
            end_date: End date string (YYYY-MM-DD)
            
        Returns:
            List of Schedule instances
        """
        query = """
            SELECT * FROM schedules 
            WHERE user_id = $1 
              AND date >= $2 
              AND date <= $3
            ORDER BY date ASC
        """
        results = await execute_query(query, user_id, start_date, end_date)
        
        return [Schedule(**row) for row in results]
    
    async def create_from_email(self, schedule_data: Dict[str, Any], user_id: str, recruit_id: Optional[int] = None) -> Schedule:
        """Create a schedule from email extraction data.
        
        Args:
            schedule_data: Extracted schedule data
            user_id: User ID for the schedule
            recruit_id: Optional recruit ID to associate
            
        Returns:
            Created Schedule instance
        """
        # Process JSON fields if needed
        if 'home_participants' in schedule_data and isinstance(schedule_data['home_participants'], list):
            schedule_data['home_participants'] = json.dumps(schedule_data['home_participants'])
            
        if 'away_participants' in schedule_data and isinstance(schedule_data['away_participants'], list):
            schedule_data['away_participants'] = json.dumps(schedule_data['away_participants'])
        
        # Create schedule model
        schedule = Schedule(
            user_id=user_id,
            recruit_id=recruit_id,
            source='email',
            **schedule_data
        )
        
        # Save to database
        return await self.create(schedule)
    
    async def get_schedules_with_recruits(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get schedules with recruit information.
        
        Args:
            user_id: User ID to filter by
            limit: Maximum number of schedules to return
            
        Returns:
            List of dictionaries with schedule and recruit info
        """
        query = """
            SELECT s.*, 
                   r.first_name, r.last_name, r.email_address, r.grad_year
            FROM schedules s
            LEFT JOIN recruits r ON s.recruit_id = r.id
            WHERE s.user_id = $1
            ORDER BY s.date DESC
            LIMIT $2
        """
        
        results = await execute_query(query, user_id, limit)
        
        # Process results to return combined dictionaries
        return results
    
    async def count_by_source(self, user_id: str) -> Dict[str, int]:
        """Count schedules by source.
        
        Args:
            user_id: User ID to filter by
            
        Returns:
            Dictionary with source counts
        """
        query = """
            SELECT source, COUNT(*) as count
            FROM schedules
            WHERE user_id = $1
            GROUP BY source
        """
        
        results = await execute_query(query, user_id)
        
        return {row['source']: row['count'] for row in results}
    
    async def get_stats_by_user(self, user_id: str) -> Dict[str, Any]:
        """Get schedule statistics for a user.
        
        Args:
            user_id: User ID to get stats for
            
        Returns:
            Dictionary with schedule statistics
        """
        stats_query = """
            SELECT 
                COUNT(*) as total_schedules,
                COUNT(DISTINCT date) as distinct_dates,
                COUNT(DISTINCT recruit_id) as distinct_recruits,
                MIN(date) as earliest_date,
                MAX(date) as latest_date
            FROM schedules
            WHERE user_id = $1
        """
        
        stats_results = await execute_query(stats_query, user_id)
        
        if not stats_results:
            return {
                "total_schedules": 0,
                "distinct_dates": 0,
                "distinct_recruits": 0,
                "earliest_date": None,
                "latest_date": None,
                "source_distribution": {}
            }
            
        # Get source distribution
        source_query = """
            SELECT source, COUNT(*) as count
            FROM schedules
            WHERE user_id = $1
            GROUP BY source
        """
        
        source_results = await execute_query(source_query, user_id)
        
        source_distribution = {row['source']: row['count'] for row in source_results}
        
        return {
            **stats_results[0],
            "source_distribution": source_distribution
        }
    
    async def delete_by_recruit(self, recruit_id: int) -> int:
        """Delete all schedules for a recruit.
        
        Args:
            recruit_id: Recruit ID to delete schedules for
            
        Returns:
            Number of deleted schedules
        """
        query = "DELETE FROM schedules WHERE recruit_id = $1 RETURNING id"
        results = await execute_query(query, recruit_id)
        
        return len(results)
    
    async def find_matching_schedule(self, date: str, event_name: Optional[str] = None, 
                                   home_team: Optional[str] = None, away_team: Optional[str] = None,
                                   user_id: Optional[str] = None) -> Optional[Schedule]:
        """Find a matching schedule based on key attributes.
        
        Args:
            date: The date of the schedule
            event_name: Optional event name to match
            home_team: Optional home team to match
            away_team: Optional away team to match
            user_id: Optional user ID to match
            
        Returns:
            Matching Schedule if found, None otherwise
        """
        conditions = ["date = $1"]
        params = [date]
        param_index = 2
        
        if event_name:
            conditions.append(f"event_name = ${param_index}")
            params.append(event_name)
            param_index += 1
            
        if home_team:
            conditions.append(f"home_team = ${param_index}")
            params.append(home_team)
            param_index += 1
            
        if away_team:
            conditions.append(f"away_team = ${param_index}")
            params.append(away_team)
            param_index += 1
            
        if user_id:
            conditions.append(f"user_id = ${param_index}")
            params.append(user_id)
            
        where_clause = " AND ".join(conditions)
        query = f"SELECT * FROM schedules WHERE {where_clause} LIMIT 1"
        
        results = await execute_query(query, *params)
        
        if not results:
            return None
            
        return Schedule(**results[0])
    
    async def associate_schedule_with_recruit(self, schedule_id: int, recruit_id: int) -> Optional[Schedule]:
        """Associate a schedule with a recruit.
        
        Args:
            schedule_id: Schedule ID to update
            recruit_id: Recruit ID to associate
            
        Returns:
            Updated Schedule if successful, None otherwise
        """
        query = """
            UPDATE schedules 
            SET recruit_id = $2, updated_at = $3
            WHERE id = $1
            RETURNING *
        """
        
        now = datetime.utcnow()
        results = await execute_query(query, schedule_id, recruit_id, now)
        
        if not results:
            return None
            
        return Schedule(**results[0])
