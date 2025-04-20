from typing import Optional, List, Dict, Any, Tuple
import json
import logging
from datetime import datetime

from models.email import Email, EmailQueue, ProcessingStatus
from .base_service import BaseService
from db.db_utils import execute_query, execute_transaction

class EmailService(BaseService[Email]):
    """Service for Email model operations."""
    
    def __init__(self):
        super().__init__(Email, 'emails')
        self.queue_service = EmailQueueService()
    
    async def get_by_user(self, user_id: str, limit: int = 100, offset: int = 0) -> List[Email]:
        """Get emails for a specific user.
        
        Args:
            user_id: User ID to filter by
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of Email instances
        """
        query = """
            SELECT * FROM emails 
            WHERE user_id = $1 
            ORDER BY received_date DESC NULLS LAST
            LIMIT $2 OFFSET $3
        """
        results = await execute_query(query, user_id, limit, offset)
        
        return [Email(**row) for row in results]
    
    async def get_by_email_id(self, email_id: str, user_id: Optional[str] = None) -> Optional[Email]:
        """Get an email by its provider email_id.
        
        Args:
            email_id: The email_id from the provider
            user_id: Optional user ID to filter by
            
        Returns:
            Email if found, None otherwise
        """
        if user_id:
            query = "SELECT * FROM emails WHERE email_id = $1 AND user_id = $2"
            results = await execute_query(query, email_id, user_id)
        else:
            query = "SELECT * FROM emails WHERE email_id = $1"
            results = await execute_query(query, email_id)
        
        if not results:
            return None
            
        return Email(**results[0])
    
    async def search_emails(self, user_id: str, search_term: str, limit: int = 20) -> List[Email]:
        """Search emails by subject or content.
        
        Args:
            user_id: User ID to filter by
            search_term: Term to search for
            limit: Maximum number of records to return
            
        Returns:
            List of matching Email instances
        """
        # Create search pattern with wildcards
        pattern = f"%{search_term}%"
        
        query = """
            SELECT * FROM emails 
            WHERE user_id = $1 
              AND (
                  LOWER(subject) LIKE LOWER($2) 
                  OR LOWER(body) LIKE LOWER($2)
                  OR LOWER(sender) LIKE LOWER($2)
              )
            ORDER BY received_date DESC NULLS LAST
            LIMIT $3
        """
        
        results = await execute_query(query, user_id, pattern, limit)
        
        return [Email(**row) for row in results]
    
    async def get_unprocessed_emails(self, user_id: Optional[str] = None, limit: int = 100) -> List[Email]:
        """Get unprocessed emails.
        
        Args:
            user_id: Optional user ID to filter by
            limit: Maximum number of records to return
            
        Returns:
            List of unprocessed Email instances
        """
        if user_id:
            query = """
                SELECT * FROM emails 
                WHERE user_id = $1 AND processed = 0
                ORDER BY received_date ASC NULLS LAST
                LIMIT $2
            """
            results = await execute_query(query, user_id, limit)
        else:
            query = """
                SELECT * FROM emails 
                WHERE processed = 0
                ORDER BY received_date ASC NULLS LAST
                LIMIT $1
            """
            results = await execute_query(query, limit)
        
        return [Email(**row) for row in results]
    
    async def mark_processed(self, email_id: int, processed: bool = True) -> Optional[Email]:
        """Mark an email as processed.
        
        Args:
            email_id: Email ID to update
            processed: Whether to mark as processed (True) or unprocessed (False)
            
        Returns:
            Updated Email if successful, None otherwise
        """
        processed_value = 1 if processed else 0
        processed_date = datetime.utcnow() if processed else None
        
        query = """
            UPDATE emails 
            SET processed = $2, 
                processed_date = $3,
                updated_at = $4
            WHERE id = $1
            RETURNING *
        """
        
        now = datetime.utcnow()
        results = await execute_query(query, email_id, processed_value, processed_date, now)
        
        if not results:
            return None
            
        return Email(**results[0])
    
    async def get_with_extraction_feedback(self, email_id: str, user_id: str) -> Tuple[Optional[Email], List[Dict[str, Any]]]:
        """Get an email with its extraction feedback.
        
        Args:
            email_id: The email_id from the provider
            user_id: User ID to filter by
            
        Returns:
            Tuple of (Email or None, list of extraction feedback dictionaries)
        """
        # First get the email
        email = await self.get_by_email_id(email_id, user_id)
        
        if not email:
            return None, []
            
        # Then get extraction feedback
        feedback_query = """
            SELECT ef.*, r.first_name, r.last_name, r.email_address
            FROM extraction_feedback ef
            JOIN recruits r ON ef.recruit_id = r.id
            WHERE ef.email_id = $1 AND ef.user_id = $2
            ORDER BY ef.created_at DESC
        """
        
        feedback = await execute_query(feedback_query, email_id, user_id)
        
        return email, feedback
    
    async def stats_by_user(self, user_id: str) -> Dict[str, Any]:
        """Get email statistics for a user.
        
        Args:
            user_id: User ID to get stats for
            
        Returns:
            Dictionary with email statistics
        """
        stats_query = """
            SELECT 
                COUNT(*) as total_emails,
                COUNT(CASE WHEN processed = 1 THEN 1 END) as processed_emails,
                COUNT(CASE WHEN has_attachments = 1 THEN 1 END) as emails_with_attachments,
                MIN(received_date) as earliest_date,
                MAX(received_date) as latest_date
            FROM emails
            WHERE user_id = $1
        """
        
        stats_results = await execute_query(stats_query, user_id)
        
        if not stats_results:
            return {
                "total_emails": 0,
                "processed_emails": 0,
                "emails_with_attachments": 0,
                "earliest_date": None,
                "latest_date": None,
                "folder_distribution": {}
            }
            
        # Get folder distribution
        folder_query = """
            SELECT folder_id, COUNT(*) as count
            FROM emails
            WHERE user_id = $1 AND folder_id IS NOT NULL
            GROUP BY folder_id
        """
        
        folder_results = await execute_query(folder_query, user_id)
        
        folder_distribution = {row['folder_id']: row['count'] for row in folder_results}
        
        return {
            **stats_results[0],
            "folder_distribution": folder_distribution
        }


class EmailQueueService(BaseService[EmailQueue]):
    """Service for EmailQueue model operations."""
    
    def __init__(self):
        super().__init__(EmailQueue, 'email_queue')
    
    async def get_queue_by_status(self, status: ProcessingStatus, limit: int = 20) -> List[EmailQueue]:
        """Get queue items by status.
        
        Args:
            status: The status to filter by
            limit: Maximum number of records to return
            
        Returns:
            List of EmailQueue instances with the specified status
        """
        query = """
            SELECT * FROM email_queue 
            WHERE status = $1
            ORDER BY priority DESC, created_at ASC
            LIMIT $2
        """
        
        results = await execute_query(query, status.value, limit)
        
        return [EmailQueue(**row) for row in results]
    
    async def get_by_user_and_status(self, user_id: str, status: ProcessingStatus, limit: int = 20) -> List[EmailQueue]:
        """Get queue items by user and status.
        
        Args:
            user_id: User ID to filter by
            status: The status to filter by
            limit: Maximum number of records to return
            
        Returns:
            List of EmailQueue instances with the specified user and status
        """
        query = """
            SELECT * FROM email_queue 
            WHERE user_id = $1 AND status = $2
            ORDER BY priority DESC, created_at ASC
            LIMIT $3
        """
        
        results = await execute_query(query, user_id, status.value, limit)
        
        return [EmailQueue(**row) for row in results]
    
    async def update_status(self, queue_id: int, status: ProcessingStatus, error_message: Optional[str] = None) -> Optional[EmailQueue]:
        """Update the status of a queue item.
        
        Args:
            queue_id: Queue item ID to update
            status: New status
            error_message: Optional error message for FAILED status
            
        Returns:
            Updated EmailQueue if successful, None otherwise
        """
        # Set processed_at timestamp if completing or failing
        processed_at = None
        if status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]:
            processed_at = datetime.utcnow()
            
        query = """
            UPDATE email_queue 
            SET status = $2, 
                processed_at = $3,
                error_message = $4,
                updated_at = $5
            WHERE id = $1
            RETURNING *
        """
        
        now = datetime.utcnow()
        results = await execute_query(query, 
                                     queue_id, 
                                     status.value, 
                                     processed_at, 
                                     error_message, 
                                     now)
        
        if not results:
            return None
            
        return EmailQueue(**results[0])
    
    async def count_by_status(self) -> Dict[str, int]:
        """Count queue items by status.
        
        Returns:
            Dictionary with status counts
        """
        query = """
            SELECT status, COUNT(*) as count
            FROM email_queue
            GROUP BY status
        """
        
        results = await execute_query(query)
        
        return {row['status']: row['count'] for row in results}
    
    async def add_to_queue(self, user_id: str, email_id: str, provider: str, folder_id: str, priority: int = 0) -> EmailQueue:
        """Add an email to the processing queue.
        
        Args:
            user_id: User ID for the queue item
            email_id: Email ID to process
            provider: Email provider (e.g., 'gmail', 'outlook')
            folder_id: Folder ID from the provider
            priority: Processing priority (higher values = higher priority)
            
        Returns:
            Created EmailQueue instance
        """
        queue_item = EmailQueue(
            user_id=user_id,
            email_id=email_id,
            provider=provider,
            folder_id=folder_id,
            status=ProcessingStatus.QUEUED,
            priority=priority
        )
        
        return await self.create(queue_item)
