from typing import Optional, List, Dict, Any, Tuple
import logging

from models.user import User, UserSettings
from .base_service import BaseService
from db.db_utils import execute_query, execute_transaction

class UserService(BaseService[User]):
    """Service for User model operations."""
    
    def __init__(self):
        super().__init__(User, 'users')
        self.settings_service = UserSettingsService()
    
    async def create_with_settings(self, user: User, settings: Optional[UserSettings] = None) -> Tuple[User, Optional[UserSettings]]:
        """Create a user with optional settings in a transaction.
        
        Args:
            user: The user to create
            settings: Optional user settings to create
            
        Returns:
            Tuple of (created user, created settings or None)
        """
        # Start with creating the user
        created_user = await self.create(user)
        
        if settings:
            # Ensure the user_id matches the created user
            settings.user_id = created_user.id
            created_settings = await self.settings_service.create(settings)
            return created_user, created_settings
        
        return created_user, None
    
    async def get_with_settings(self, user_id: str) -> Tuple[Optional[User], Optional[UserSettings]]:
        """Get a user and their settings.
        
        Args:
            user_id: The user ID to look up
            
        Returns:
            Tuple of (user or None, settings or None)
        """
        user = await self.get_by_id(user_id)
        
        if not user:
            return None, None
            
        settings = await self.settings_service.get_by_user_id(user_id)
        return user, settings
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email.
        
        Args:
            email: Email address to look up
            
        Returns:
            User if found, None otherwise
        """
        results = await self.find_by(email=email)
        return results[0] if results else None
    
    async def delete_with_settings(self, user_id: str) -> bool:
        """Delete a user and their settings.
        
        Args:
            user_id: The user ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        # Check if user exists
        user = await self.get_by_id(user_id)
        if not user:
            return False
            
        # Delete settings (if any)
        await self.settings_service.delete_by_user_id(user_id)
        
        # Delete user
        return await self.delete(user_id)
    
    async def update_with_settings(self, user_id: str, user_data: Dict[str, Any], settings_data: Optional[Dict[str, Any]] = None) -> Tuple[Optional[User], Optional[UserSettings]]:
        """Update a user and optionally their settings.
        
        Args:
            user_id: The user ID to update
            user_data: Dict of user fields to update
            settings_data: Optional dict of settings fields to update
            
        Returns:
            Tuple of (updated user or None, updated settings or None)
        """
        # Update user
        updated_user = await self.update(user_id, user_data)
        
        if not updated_user:
            return None, None
            
        # Update settings if provided
        updated_settings = None
        if settings_data:
            settings = await self.settings_service.get_by_user_id(user_id)
            
            if settings:
                # Update existing settings
                updated_settings = await self.settings_service.update_by_user_id(user_id, settings_data)
            else:
                # Create new settings
                settings_data['user_id'] = user_id
                settings = UserSettings(**settings_data)
                updated_settings = await self.settings_service.create(settings)
                
        return updated_user, updated_settings
    
    async def get_admin_users(self) -> List[User]:
        """Get all admin users.
        
        Returns:
            List of admin users
        """
        return await self.find_by(is_admin=True)


class UserSettingsService(BaseService[UserSettings]):
    """Service for UserSettings model operations."""
    
    def __init__(self):
        super().__init__(UserSettings, 'user_settings')
    
    async def get_by_user_id(self, user_id: str) -> Optional[UserSettings]:
        """Get settings by user ID.
        
        Args:
            user_id: The user ID to look up
            
        Returns:
            UserSettings if found, None otherwise
        """
        query = f"SELECT * FROM {self.table_name} WHERE user_id = $1"
        results = await execute_query(query, user_id)
        
        if not results:
            return None
            
        return UserSettings(**results[0])
    
    async def update_by_user_id(self, user_id: str, data: Dict[str, Any]) -> Optional[UserSettings]:
        """Update settings by user ID.
        
        Args:
            user_id: The user ID to update
            data: Dict of fields to update
            
        Returns:
            Updated UserSettings if found and updated, None otherwise
        """
        if not data:
            return await self.get_by_user_id(user_id)
            
        # Build the query
        set_clause = ', '.join(f"{k} = ${i+2}" for i, k in enumerate(data.keys()))
        values = list(data.values())
        
        query = f"UPDATE {self.table_name} SET {set_clause} WHERE user_id = $1 RETURNING *"
        
        results = await execute_query(query, user_id, *values)
        
        if not results:
            return None
            
        return UserSettings(**results[0])
    
    async def delete_by_user_id(self, user_id: str) -> bool:
        """Delete settings by user ID.
        
        Args:
            user_id: The user ID to delete
            
        Returns:
            True if deleted successfully, False if not found
        """
        query = f"DELETE FROM {self.table_name} WHERE user_id = $1 RETURNING user_id"
        results = await execute_query(query, user_id)
        
        return len(results) > 0
