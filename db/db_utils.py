import os
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
import asyncpg
from contextvars import ContextVar

logger = logging.getLogger(__name__)

# Context variable to store the connection pool for the current context
pool_var: ContextVar[Optional[asyncpg.Pool]] = ContextVar('pool', default=None)

async def get_pool() -> asyncpg.Pool:
    """Get or create a connection pool for the current context."""
    pool = pool_var.get()
    if pool is None:
        # Get database connection parameters from environment variables
        user = os.getenv('DB_USER', 'postgres')
        password = os.getenv('DB_PASSWORD', 'postgres')
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '5432')
        database = os.getenv('DB_NAME', 'recruiting')
        
        # Create a connection pool
        pool = await asyncpg.create_pool(
            user=user,
            password=password,
            host=host,
            port=port,
            database=database,
            min_size=5,
            max_size=20
        )
        pool_var.set(pool)
    return pool

async def execute_query(query: str, *args, fetch: bool = True) -> Union[List[Dict[str, Any]], None]:
    """Execute a SQL query and return the results.
    
    Args:
        query: SQL query to execute
        *args: Parameters for the query
        fetch: Whether to fetch and return results (True) or just execute (False)
        
    Returns:
        List of dictionaries representing rows, or None if fetch=False
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            if fetch:
                rows = await conn.fetch(query, *args)
                return [dict(row) for row in rows]
            else:
                await conn.execute(query, *args)
                return None
        except Exception as e:
            logger.error(f"Database error executing query: {e}")
            logger.debug(f"Query: {query}, Args: {args}")
            raise

async def execute_transaction(queries: List[Tuple[str, List[Any]]]) -> None:
    """Execute multiple queries in a transaction.
    
    Args:
        queries: List of tuples containing (query, args)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            for query, args in queries:
                await conn.execute(query, *args)

async def close_pool():
    """Close the connection pool."""
    pool = pool_var.get()
    if pool:
        await pool.close()
        pool_var.set(None)
