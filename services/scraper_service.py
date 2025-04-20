from typing import Optional, List, Dict, Any, Tuple
import json
import logging
from datetime import datetime

from models.scraper import ScraperConfiguration, ScrapingLog
from .base_service import BaseService
from db.db_utils import execute_query, execute_transaction

class ScraperService(BaseService[ScraperConfiguration]):
    """Service for ScraperConfiguration model operations."""
    
    def __init__(self):
        super().__init__(ScraperConfiguration, 'scraper_configurations')
        self.log_service = ScrapingLogService()
    
    async def get_by_source(self, source: str) -> List[ScraperConfiguration]:
        """Get all configurations for a specific source.
        
        Args:
            source: Source to filter by
            
        Returns:
            List of ScraperConfiguration instances for the source
        """
        query = """
            SELECT * FROM scraper_configurations
            WHERE source = $1
            ORDER BY name
        """
        
        results = await execute_query(query, source)
        
        return [ScraperConfiguration(**row) for row in results]
    
    async def get_active_configurations(self) -> List[ScraperConfiguration]:
        """Get all active scraper configurations.
        
        Returns:
            List of active ScraperConfiguration instances
        """
        query = """
            SELECT * FROM scraper_configurations
            WHERE active = TRUE
            ORDER BY source, name
        """
        
        results = await execute_query(query)
        
        return [ScraperConfiguration(**row) for row in results]
    
    async def toggle_active(self, config_id: int, active: bool) -> Optional[ScraperConfiguration]:
        """Toggle the active status of a configuration.
        
        Args:
            config_id: Configuration ID to update
            active: New active status
            
        Returns:
            Updated ScraperConfiguration if successful, None if not found
        """
        query = """
            UPDATE scraper_configurations
            SET active = $2, updated_at = $3
            WHERE id = $1
            RETURNING *
        """
        
        now = datetime.utcnow()
        results = await execute_query(query, config_id, active, now)
        
        if not results:
            return None
            
        return ScraperConfiguration(**results[0])
    
    async def create_configuration(self, name: str, source: str, parameters: Dict[str, Any], active: bool = True) -> ScraperConfiguration:
        """Create a new scraper configuration.
        
        Args:
            name: Name of the configuration
            source: Source website or service
            parameters: Dictionary of scraper parameters
            active: Whether the configuration is active
            
        Returns:
            Created ScraperConfiguration instance
        """
        # Create the configuration model
        config = ScraperConfiguration(
            name=name,
            source=source,
            parameters=parameters,
            active=active
        )
        
        # Save to database
        return await self.create(config)
    
    async def update_parameters(self, config_id: int, parameters: Dict[str, Any]) -> Optional[ScraperConfiguration]:
        """Update the parameters of a configuration.
        
        Args:
            config_id: Configuration ID to update
            parameters: New parameters dictionary
            
        Returns:
            Updated ScraperConfiguration if successful, None if not found
        """
        # Convert parameters to JSON string
        params_json = json.dumps(parameters)
        
        query = """
            UPDATE scraper_configurations
            SET parameters = $2, updated_at = $3
            WHERE id = $1
            RETURNING *
        """
        
        now = datetime.utcnow()
        results = await execute_query(query, config_id, params_json, now)
        
        if not results:
            return None
            
        return ScraperConfiguration(**results[0])
    
    async def get_with_latest_log(self, config_id: int) -> Tuple[Optional[ScraperConfiguration], Optional[ScrapingLog]]:
        """Get a configuration with its latest log.
        
        Args:
            config_id: Configuration ID to look up
            
        Returns:
            Tuple of (ScraperConfiguration or None, latest ScrapingLog or None)
        """
        # Get the configuration
        config = await self.get_by_id(config_id)
        
        if not config:
            return None, None
            
        # Get the latest log
        latest_log = await self.log_service.get_latest_for_config(config_id)
        
        return config, latest_log
    
    async def create_log_entry(self, config_id: int, start_time: datetime, 
                              end_time: Optional[datetime] = None,
                              total_matches: int = 0, new_matches: int = 0,
                              results: Optional[Dict[str, Any]] = None,
                              error: Optional[str] = None) -> ScrapingLog:
        """Create a new scraping log entry.
        
        Args:
            config_id: Configuration ID the log is for
            start_time: When the scrape started
            end_time: When the scrape ended (None if still running)
            total_matches: Total matches found
            new_matches: New matches found
            results: Optional dictionary of detailed results
            error: Optional error message if the scrape failed
            
        Returns:
            Created ScrapingLog instance
        """
        # Calculate duration if end_time is provided
        duration_seconds = None
        if end_time and start_time:
            duration_seconds = int((end_time - start_time).total_seconds())
        
        # Create the log model
        log = ScrapingLog(
            config_id=config_id,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration_seconds,
            total_matches=total_matches,
            new_matches=new_matches,
            results=results or {},
            error=error
        )
        
        # Save to database
        return await self.log_service.create(log)
    
    async def update_log_entry(self, log_id: int, end_time: datetime,
                              total_matches: int, new_matches: int,
                              results: Optional[Dict[str, Any]] = None,
                              error: Optional[str] = None) -> Optional[ScrapingLog]:
        """Update an existing log entry when a scrape finishes.
        
        Args:
            log_id: Log ID to update
            end_time: When the scrape ended
            total_matches: Total matches found
            new_matches: New matches found
            results: Optional dictionary of detailed results
            error: Optional error message if the scrape failed
            
        Returns:
            Updated ScrapingLog if successful, None if not found
        """
        # Get the existing log to calculate duration
        log = await self.log_service.get_by_id(log_id)
        
        if not log:
            return None
            
        # Calculate duration
        duration_seconds = int((end_time - log.start_time).total_seconds())
        
        # Convert results to JSON string if provided
        results_json = json.dumps(results) if results else None
        
        query = """
            UPDATE scraping_logs
            SET end_time = $2,
                duration_seconds = $3,
                total_matches = $4,
                new_matches = $5,
                results = $6,
                error = $7
            WHERE id = $1
            RETURNING *
        """
        
        results = await execute_query(query, log_id, end_time, duration_seconds, 
                                    total_matches, new_matches, results_json, error)
        
        if not results:
            return None
            
        return ScrapingLog(**results[0])


class ScrapingLogService(BaseService[ScrapingLog]):
    """Service for ScrapingLog model operations."""
    
    def __init__(self):
        super().__init__(ScrapingLog, 'scraping_logs')
    
    async def get_by_config(self, config_id: int, limit: int = 10) -> List[ScrapingLog]:
        """Get logs for a specific configuration.
        
        Args:
            config_id: Configuration ID to filter by
            limit: Maximum number of logs to return
            
        Returns:
            List of ScrapingLog instances for the configuration
        """
        query = """
            SELECT * FROM scraping_logs
            WHERE config_id = $1
            ORDER BY start_time DESC
            LIMIT $2
        """
        
        results = await execute_query(query, config_id, limit)
        
        return [ScrapingLog(**row) for row in results]
    
    async def get_latest_for_config(self, config_id: int) -> Optional[ScrapingLog]:
        """Get the latest log for a configuration.
        
        Args:
            config_id: Configuration ID to filter by
            
        Returns:
            Latest ScrapingLog instance or None if no logs exist
        """
        query = """
            SELECT * FROM scraping_logs
            WHERE config_id = $1
            ORDER BY start_time DESC
            LIMIT 1
        """
        
        results = await execute_query(query, config_id)
        
        if not results:
            return None
            
        return ScrapingLog(**results[0])
    
    async def get_logs_with_errors(self, limit: int = 20) -> List[ScrapingLog]:
        """Get logs that have errors.
        
        Args:
            limit: Maximum number of logs to return
            
        Returns:
            List of ScrapingLog instances with errors
        """
        query = """
            SELECT * FROM scraping_logs
            WHERE error IS NOT NULL
            ORDER BY start_time DESC
            LIMIT $1
        """
        
        results = await execute_query(query, limit)
        
        return [ScrapingLog(**row) for row in results]
    
    async def get_successful_logs(self, days: int = 7) -> List[ScrapingLog]:
        """Get successful logs from the last X days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of successful ScrapingLog instances
        """
        # Calculate the date range
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        query = """
            SELECT * FROM scraping_logs
            WHERE error IS NULL
              AND end_time IS NOT NULL
              AND start_time >= $1
            ORDER BY start_time DESC
        """
        
        results = await execute_query(query, cutoff_date)
        
        return [ScrapingLog(**row) for row in results]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about scraping logs.
        
        Returns:
            Dictionary with log statistics
        """
        stats_query = """
            SELECT 
                COUNT(*) as total_logs,
                COUNT(CASE WHEN error IS NULL AND end_time IS NOT NULL THEN 1 END) as successful_logs,
                COUNT(CASE WHEN error IS NOT NULL THEN 1 END) as failed_logs,
                SUM(CASE WHEN error IS NULL THEN total_matches ELSE 0 END) as total_matches,
                SUM(CASE WHEN error IS NULL THEN new_matches ELSE 0 END) as total_new_matches,
                AVG(CASE WHEN error IS NULL AND duration_seconds IS NOT NULL THEN duration_seconds ELSE NULL END) as avg_duration
            FROM scraping_logs
        """
        
        stats_results = await execute_query(stats_query)
        
        if not stats_results:
            return {
                "total_logs": 0,
                "successful_logs": 0,
                "failed_logs": 0,
                "total_matches": 0,
                "total_new_matches": 0,
                "avg_duration": 0
            }
            
        return stats_results[0]
