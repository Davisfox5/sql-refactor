from typing import Optional, List, Dict, Any, Tuple
import json
import logging
import hashlib
from datetime import datetime, timedelta

from models.gpt_cache import GPTCache
from .base_service import BaseService
from db.db_utils import execute_query, execute_transaction

class GPTCacheService(BaseService[GPTCache]):
    """Service for GPTCache model operations."""
    
    def __init__(self):
        super().__init__(GPTCache, 'gpt_cache')
    
    async def get_by_content_hash(self, content_hash: str) -> Optional[GPTCache]:
        """Get a cache entry by content hash.
        
        Args:
            content_hash: Content hash to look up
            
        Returns:
            GPTCache if found, None otherwise
        """
        query = "SELECT * FROM gpt_cache WHERE content_hash = $1"
        results = await execute_query(query, content_hash)
        
        if not results:
            return None
            
        return GPTCache(**results[0])
    
    async def get_by_email(self, email: str) -> List[GPTCache]:
        """Get all cache entries for a specific email.
        
        Args:
            email: Email address to filter by
            
        Returns:
            List of GPTCache instances for the email
        """
        query = """
            SELECT * FROM gpt_cache
            WHERE email = $1
            ORDER BY updated_at DESC
        """
        
        results = await execute_query(query, email)
        
        return [GPTCache(**row) for row in results]
    
    async def create_or_update(self, content: str, result: Dict[str, Any], email: Optional[str] = None) -> GPTCache:
        """Create a new cache entry or update an existing one.
        
        Args:
            content: Content to hash and cache
            result: Result to cache
            email: Optional email address to associate with this cache entry
            
        Returns:
            Created or updated GPTCache instance
        """
        # Generate content hash
        content_hash = self.generate_hash(content)
        
        # Check if entry exists
        existing = await self.get_by_content_hash(content_hash)
        
        if existing:
            # Update existing entry
            query = """
                UPDATE gpt_cache
                SET result_json = $2, 
                    email = $3,
                    updated_at = $4
                WHERE content_hash = $1
                RETURNING *
            """
            
            now = datetime.utcnow()
            result_json = json.dumps(result)
            results = await execute_query(query, content_hash, result_json, email, now)
            
            return GPTCache(**results[0])
        else:
            # Create new entry
            cache = GPTCache(
                content_hash=content_hash,
                email=email,
                result_json=result
            )
            
            return await self.create(cache)
    
    async def delete_old_entries(self, days: int = 30) -> int:
        """Delete cache entries older than specified days.
        
        Args:
            days: Age in days of entries to delete
            
        Returns:
            Number of deleted entries
        """
        cutoff_date = (datetime.utcnow() - timedelta(days=days))
        
        query = "DELETE FROM gpt_cache WHERE updated_at < $1 RETURNING id"
        results = await execute_query(query, cutoff_date)
        
        return len(results)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about cache usage.
        
        Returns:
            Dictionary with cache statistics
        """
        stats_query = """
            SELECT 
                COUNT(*) as total_entries,
                COUNT(DISTINCT email) as distinct_emails,
                MIN(created_at) as oldest_entry,
                MAX(updated_at) as newest_entry
            FROM gpt_cache
        """
        
        stats_results = await execute_query(stats_query)
        
        if not stats_results:
            return {
                "total_entries": 0,
                "distinct_emails": 0,
                "oldest_entry": None,
                "newest_entry": None,
                "size_estimate_kb": 0
            }
        
        # Calculate approximate size (rough estimate)
        size_query = """
            SELECT 
                SUM(LENGTH(result_json)) as total_json_size
            FROM gpt_cache
        """
        
        size_results = await execute_query(size_query)
        size_kb = 0
        
        if size_results and size_results[0]['total_json_size']:
            # Converting bytes to KB (rough estimate)
            size_kb = size_results[0]['total_json_size'] / 1024
            
        return {
            **stats_results[0],
            "size_estimate_kb": size_kb
        }
    
    def generate_hash(self, content: str) -> str:
        """Generate a hash from content.
        
        Args:
            content: Content to hash
            
        Returns:
            MD5 hash as hexadecimal string
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()
