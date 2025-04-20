from typing import List, Dict, Any, Optional, TypeVar, Generic, Type, Union
import logging
from pydantic import BaseModel

from db.db_utils import execute_query, execute_transaction

# Type variable for use with generic methods
T = TypeVar('T', bound=BaseModel)

class BaseService(Generic[T]):
    """Base service class with common CRUD operations for all models."""
    
    def __init__(self, model_class: Type[T], table_name: str):
        """Initialize with model class and table name.
        
        Args:
            model_class: The Pydantic model class
            table_name: The database table name
        """
        self.model_class = model_class
        self.table_name = table_name
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    async def get_by_id(self, id_value: Union[str, int]) -> Optional[T]:
        """Get a single record by ID.
        
        Args:
            id_value: The ID value to look up
            
        Returns:
            The model instance or None if not found
        """
        query = f"SELECT * FROM {self.table_name} WHERE id = $1"
        results = await execute_query(query, id_value)
        
        if not results:
            return None
            
        return self.model_class(**results[0])
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Get all records with pagination.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of model instances
        """
        query = f"SELECT * FROM {self.table_name} ORDER BY id LIMIT $1 OFFSET $2"
        results = await execute_query(query, limit, offset)
        
        return [self.model_class(**row) for row in results]
    
    async def create(self, obj: T) -> T:
        """Create a new record.
        
        Args:
            obj: The model instance to create
            
        Returns:
            The created model instance with database-assigned values (like ID)
        """
        # Convert model to dict, removing None values
        data = obj.model_dump(exclude_none=True)
        
        # Remove id if it's None or auto-assigned
        if 'id' in data and (data['id'] is None or self._is_id_auto_assigned()):
            del data['id']
        
        # Build the query
        columns = ', '.join(data.keys())
        placeholders = ', '.join(f'${i+1}' for i in range(len(data)))
        values = list(data.values())
        
        query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders}) RETURNING *"
        
        results = await execute_query(query, *values)
        
        return self.model_class(**results[0])
    
    async def update(self, id_value: Union[str, int], obj: Union[T, Dict[str, Any]]) -> Optional[T]:
        """Update an existing record.
        
        Args:
            id_value: The ID of the record to update
            obj: Either a model instance or a dict of fields to update
            
        Returns:
            The updated model instance or None if not found
        """
        # Convert to dict if it's a model
        if isinstance(obj, BaseModel):
            data = obj.model_dump(exclude_none=True)
        else:
            data = obj
            
        # Remove id from the update data
        if 'id' in data:
            del data['id']
            
        # Handle the case where there's nothing to update
        if not data:
            return await self.get_by_id(id_value)
            
        # Build the query
        set_clause = ', '.join(f"{k} = ${i+2}" for i, k in enumerate(data.keys()))
        values = list(data.values())
        
        query = f"UPDATE {self.table_name} SET {set_clause} WHERE id = $1 RETURNING *"
        
        results = await execute_query(query, id_value, *values)
        
        if not results:
            return None
            
        return self.model_class(**results[0])
    
    async def delete(self, id_value: Union[str, int]) -> bool:
        """Delete a record by ID.
        
        Args:
            id_value: The ID of the record to delete
            
        Returns:
            True if deleted successfully, False if not found
        """
        query = f"DELETE FROM {self.table_name} WHERE id = $1 RETURNING id"
        results = await execute_query(query, id_value)
        
        return len(results) > 0
    
    async def find_by(self, **kwargs) -> List[T]:
        """Find records matching the given criteria.
        
        Args:
            **kwargs: Field=value pairs to filter by
            
        Returns:
            List of matching model instances
        """
        if not kwargs:
            return await self.get_all()
            
        conditions = []
        values = []
        i = 1
        
        for key, value in kwargs.items():
            conditions.append(f"{key} = ${i}")
            values.append(value)
            i += 1
            
        where_clause = ' AND '.join(conditions)
        query = f"SELECT * FROM {self.table_name} WHERE {where_clause}"
        
        results = await execute_query(query, *values)
        
        return [self.model_class(**row) for row in results]
    
    async def count(self, **kwargs) -> int:
        """Count records matching the given criteria.
        
        Args:
            **kwargs: Field=value pairs to filter by
            
        Returns:
            Count of matching records
        """
        if not kwargs:
            query = f"SELECT COUNT(*) as count FROM {self.table_name}"
            results = await execute_query(query)
        else:
            conditions = []
            values = []
            i = 1
            
            for key, value in kwargs.items():
                conditions.append(f"{key} = ${i}")
                values.append(value)
                i += 1
                
            where_clause = ' AND '.join(conditions)
            query = f"SELECT COUNT(*) as count FROM {self.table_name} WHERE {where_clause}"
            results = await execute_query(query, *values)
            
        return results[0]['count']
    
    def _is_id_auto_assigned(self) -> bool:
        """Check if the ID is auto-assigned by the database.
        
        Override this in subclasses if needed.
        
        Returns:
            True if ID is auto-assigned, False otherwise
        """
        # Default assumption is that integer IDs are auto-assigned
        # and string IDs are not (they're usually UUIDs)
        annotations = getattr(self.model_class, '__annotations__', {})
        id_type = annotations.get('id', None)
        
        if id_type is None:
            return False
            
        return getattr(id_type, '__origin__', id_type) is int
