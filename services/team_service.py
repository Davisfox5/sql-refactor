from typing import Optional, List, Dict, Any, Tuple, Set
import logging
from datetime import datetime

from models.team import Team, TeamAlias
from .base_service import BaseService
from db.db_utils import execute_query, execute_transaction

class TeamService(BaseService[Team]):
    """Service for Team model operations."""
    
    def __init__(self):
        super().__init__(Team, 'teams')
        self.alias_service = TeamAliasService()
    
    async def get_by_name(self, name: str, normalized: bool = False) -> Optional[Team]:
        """Get a team by name.
        
        Args:
            name: The team name to look up
            normalized: Whether to look up by normalized_name (True) or name (False)
            
        Returns:
            Team if found, None otherwise
        """
        if normalized:
            query = "SELECT * FROM teams WHERE normalized_name = $1"
            results = await execute_query(query, self._normalize_name(name))
        else:
            query = "SELECT * FROM teams WHERE name = $1"
            results = await execute_query(query, name)
        
        if not results:
            return None
            
        return Team(**results[0])
    
    async def find_by_alias(self, alias: str) -> Optional[Team]:
        """Find a team by any of its aliases.
        
        Args:
            alias: The alias to look up
            
        Returns:
            Team if found, None otherwise
        """
        query = """
            SELECT t.* 
            FROM teams t
            JOIN team_aliases ta ON t.id = ta.team_id
            WHERE ta.alias = $1
            LIMIT 1
        """
        
        results = await execute_query(query, alias)
        
        if not results:
            return None
            
        return Team(**results[0])
    
    async def get_or_create(self, name: str, **kwargs) -> Tuple[Team, bool]:
        """Get an existing team or create it if it doesn't exist.
        
        Args:
            name: The team name
            **kwargs: Additional team attributes
            
        Returns:
            Tuple of (Team, created) where created is True if a new team was created
        """
        # Check if team exists by normalized name
        normalized_name = self._normalize_name(name)
        team = await self.get_by_name(normalized_name, normalized=True)
        
        if team:
            return team, False
            
        # Team doesn't exist, create it
        team_data = {
            "name": name,
            "normalized_name": normalized_name,
            **kwargs
        }
        
        team = Team(**team_data)
        created_team = await self.create(team)
        
        return created_team, True
    
    async def get_with_aliases(self, team_id: int) -> Tuple[Optional[Team], List[TeamAlias]]:
        """Get a team with all its aliases.
        
        Args:
            team_id: Team ID to look up
            
        Returns:
            Tuple of (Team or None, list of TeamAlias instances)
        """
        # Get the team
        team = await self.get_by_id(team_id)
        
        if not team:
            return None, []
            
        # Get all aliases
        aliases = await self.alias_service.get_by_team(team_id)
        
        return team, aliases
    
    async def add_alias(self, team_id: int, alias: str, source: Optional[str] = None) -> Optional[TeamAlias]:
        """Add an alias to a team.
        
        Args:
            team_id: Team ID to add alias to
            alias: The alias to add
            source: Optional source of the alias
            
        Returns:
            Created TeamAlias if successful, None if team not found
        """
        # Check if team exists
        team = await self.get_by_id(team_id)
        
        if not team:
            return None
            
        # Check if alias already exists
        existing_alias = await self.alias_service.get_by_alias(alias)
        
        if existing_alias:
            # Alias already exists, return it
            return existing_alias
            
        # Create new alias
        alias_data = {
            "team_id": team_id,
            "alias": alias,
            "source": source
        }
        
        alias = TeamAlias(**alias_data)
        created_alias = await self.alias_service.create(alias)
        
        return created_alias
    
    async def find_matching_team(self, team_name: str) -> Optional[Team]:
        """Find a team that matches a given name (either exact or by alias).
        
        Args:
            team_name: Team name to match
            
        Returns:
            Matching Team if found, None otherwise
        """
        # Try exact match first
        team = await self.get_by_name(team_name)
        
        if team:
            return team
            
        # Try normalized match
        team = await self.get_by_name(self._normalize_name(team_name), normalized=True)
        
        if team:
            return team
            
        # Try alias match
        team = await self.find_by_alias(team_name)
        
        return team
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about teams.
        
        Returns:
            Dictionary with team statistics
        """
        stats_query = """
            SELECT 
                COUNT(*) as total_teams,
                COUNT(DISTINCT birth_year) as distinct_birth_years,
                COUNT(DISTINCT gender) as distinct_genders,
                COUNT(DISTINCT age_group) as distinct_age_groups
            FROM teams
        """
        
        stats_results = await execute_query(stats_query)
        
        if not stats_results:
            return {
                "total_teams": 0,
                "distinct_birth_years": 0,
                "distinct_genders": 0,
                "distinct_age_groups": 0,
                "birth_year_distribution": {},
                "gender_distribution": {},
                "age_group_distribution": {}
            }
            
        # Get birth year distribution
        birth_year_query = """
            SELECT birth_year, COUNT(*) as count
            FROM teams
            WHERE birth_year IS NOT NULL
            GROUP BY birth_year
            ORDER BY birth_year
        """
        
        birth_year_results = await execute_query(birth_year_query)
        birth_year_distribution = {row['birth_year']: row['count'] for row in birth_year_results}
        
        # Get gender distribution
        gender_query = """
            SELECT gender, COUNT(*) as count
            FROM teams
            WHERE gender IS NOT NULL
            GROUP BY gender
        """
        
        gender_results = await execute_query(gender_query)
        gender_distribution = {row['gender']: row['count'] for row in gender_results}
        
        # Get age group distribution
        age_group_query = """
            SELECT age_group, COUNT(*) as count
            FROM teams
            WHERE age_group IS NOT NULL
            GROUP BY age_group
        """
        
        age_group_results = await execute_query(age_group_query)
        age_group_distribution = {row['age_group']: row['count'] for row in age_group_results}
        
        return {
            **stats_results[0],
            "birth_year_distribution": birth_year_distribution,
            "gender_distribution": gender_distribution,
            "age_group_distribution": age_group_distribution
        }
    
    def _normalize_name(self, name: str) -> str:
        """Normalize a team name for matching purposes.
        
        Args:
            name: Team name to normalize
            
        Returns:
            Normalized team name
        """
        # Basic normalization - replace with actual logic used in the app
        if not name:
            return ""
            
        return name.lower().replace(' ', '_').replace('-', '_').replace('.', '')


class TeamAliasService(BaseService[TeamAlias]):
    """Service for TeamAlias model operations."""
    
    def __init__(self):
        super().__init__(TeamAlias, 'team_aliases')
    
    async def get_by_team(self, team_id: int) -> List[TeamAlias]:
        """Get all aliases for a team.
        
        Args:
            team_id: Team ID to get aliases for
            
        Returns:
            List of TeamAlias instances
        """
        query = """
            SELECT * FROM team_aliases 
            WHERE team_id = $1
            ORDER BY alias
        """
        
        results = await execute_query(query, team_id)
        
        return [TeamAlias(**row) for row in results]
    
    async def get_by_alias(self, alias: str) -> Optional[TeamAlias]:
        """Get a team alias by the alias string.
        
        Args:
            alias: The alias string to look up
            
        Returns:
            TeamAlias if found, None otherwise
        """
        query = "SELECT * FROM team_aliases WHERE alias = $1"
        results = await execute_query(query, alias)
        
        if not results:
            return None
            
        return TeamAlias(**results[0])
    
    async def get_by_source(self, source: str) -> List[TeamAlias]:
        """Get all aliases from a specific source.
        
        Args:
            source: Source to filter by
            
        Returns:
            List of TeamAlias instances from the source
        """
        query = """
            SELECT * FROM team_aliases 
            WHERE source = $1
            ORDER BY alias
        """
        
        results = await execute_query(query, source)
        
        return [TeamAlias(**row) for row in results]
    
    async def bulk_create_aliases(self, team_id: int, aliases: List[str], source: Optional[str] = None) -> List[TeamAlias]:
        """Create multiple aliases for a team in a single transaction.
        
        Args:
            team_id: Team ID to add aliases to
            aliases: List of alias strings to add
            source: Optional source of the aliases
            
        Returns:
            List of created TeamAlias instances
        """
        created_aliases = []
        
        # Start a transaction to create all aliases
        try:
            for alias_str in aliases:
                # Skip duplicates
                existing_alias = await self.get_by_alias(alias_str)
                
                if existing_alias:
                    # Skip if already exists for this team
                    if existing_alias.team_id == team_id:
                        created_aliases.append(existing_alias)
                        continue
                    
                    # Skip if exists for another team
                    continue
                
                # Create new alias
                alias = TeamAlias(
                    team_id=team_id,
                    alias=alias_str,
                    source=source
                )
                
                created_alias = await self.create(alias)
                created_aliases.append(created_alias)
                
            return created_aliases
        except Exception as e:
            self.logger.error(f"Error bulk creating aliases: {e}")
            return created_aliases
