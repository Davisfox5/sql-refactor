# SQL Refactor - From SQLAlchemy ORM to Raw SQL with Pydantic

This repository contains code for the refactoring of a recruiting application from SQLAlchemy ORM to raw SQL queries with Pydantic models. The goal was to maintain all existing model functionality while moving away from the ORM pattern.

## Project Structure

```
├── db/
│   └── db_utils.py      # Database connection utilities
├── models/
│   ├── base.py          # Base model class
│   ├── user.py          # User and UserSettings models
│   ├── recruit.py       # Recruit model
│   ├── schedule.py      # Schedule model
│   ├── email.py         # Email and EmailQueue models
│   ├── feedback.py      # ExtractionFeedback and ExtractionPattern models
│   ├── team.py          # Team and TeamAlias models
│   ├── scraper.py       # ScraperConfiguration and ScrapingLog models
│   └── gpt_cache.py     # GPTCache model
├── services/
│   ├── base_service.py  # Base service with CRUD operations
│   ├── user_service.py  # User-related services
│   ├── recruit_service.py  # Recruit-related services
│   ├── schedule_service.py # Schedule-related services
│   ├── email_service.py    # Email-related services
│   ├── extraction_service.py # Extraction feedback services
│   ├── team_service.py     # Team-related services
│   ├── scraper_service.py  # Scraper-related services
│   └── gpt_cache_service.py # GPT cache services
└── migrations/
    └── schema.sql       # SQL schema for migrations
```

## Key Concepts

### 1. Pydantic Models

- All models use `Pydantic` instead of SQLAlchemy ORM
- Type hints ensure field validation
- Models maintain compatibility with existing code through consistent field names
- `to_dict()` method for serialization is preserved

### 2. Raw SQL with asyncpg

- All database queries use raw SQL via `asyncpg`
- Consistent formatting with positional parameters (`$1`, `$2`, etc.)
- Transactions are used when necessary for data integrity
- All queries are properly parameterized to prevent SQL injection

### 3. Service Layer

- Each model has a corresponding service class
- Services handle CRUD operations and complex queries
- All relationships are explicit through service methods
- Methods follow consistent patterns for ease of use

## How to Use

### Basic CRUD Operations

Each service class provides standard CRUD operations:

```python
# Create a new user
user = User(email="user@example.com", name="John Doe")
user_service = UserService()
created_user = await user_service.create(user)

# Get a user by ID
user = await user_service.get_by_id("user-uuid")

# Update a user
updated_user = await user_service.update("user-uuid", {"name": "Jane Doe"})

# Delete a user
success = await user_service.delete("user-uuid")

# Find users by criteria
admins = await user_service.find_by(is_admin=True)

# Count users
total_users = await user_service.count()
```

### Handling Relationships

Relationships are handled explicitly through service methods:

```python
# Get a user with their settings
user_service = UserService()
user, settings = await user_service.get_with_settings("user-uuid")

# Get a recruit with their schedules
recruit_service = RecruitService()
recruit, schedules = await recruit_service.get_recruit_with_schedules(recruit_id)

# Get a team with its aliases
team_service = TeamService()
team, aliases = await team_service.get_with_aliases(team_id)
```

### Complex Queries

Each service provides methods for more complex operations:

```python
# Get upcoming schedules for a user
schedule_service = ScheduleService()
upcoming = await schedule_service.get_upcoming_schedules(user_id, days=30)

# Search emails
email_service = EmailService()
results = await email_service.search_emails(user_id, search_term="interview")

# Get statistics
stats = await recruit_service.get_stats_by_user(user_id)
```

## Database Connection

The database connection is managed through the `db_utils.py` module:

```python
from db.db_utils import execute_query, execute_transaction

# Execute a simple query
results = await execute_query("SELECT * FROM users WHERE id = $1", user_id)

# Execute multiple queries in a transaction
await execute_transaction([
    ("DELETE FROM schedules WHERE recruit_id = $1", [recruit_id]),
    ("DELETE FROM recruits WHERE id = $1", [recruit_id])
])
```

## Migrations

The `migrations/schema.sql` file contains the complete database schema. You can use it to:

1. Initialize a new database
2. Create migration scripts for schema changes
3. Understand the table structure and relationships

## Error Handling

Each service method includes appropriate error handling:

- Invalid inputs are caught through Pydantic validation
- Database errors are logged and propagated
- Not-found conditions return `None` or empty lists as appropriate

## Testing

To test the services:

1. Create a test database
2. Use the schema.sql to initialize the schema
3. Write tests that use the service methods with test data
4. Verify the results against expected outcomes

## Performance Considerations

- Use `get_by_id` when fetching a single record by primary key
- Use `find_by` with specific criteria to limit result sets
- For large result sets, use the `limit` and `offset` parameters for pagination
- Use transactions when making multiple related changes

## Migrating from SQLAlchemy

If you're migrating existing code that used SQLAlchemy:

1. Replace `Model.query.filter_by(...)` with `service.find_by(...)`
2. Replace `db.session.add(model)` with `await service.create(model)`
3. Replace `db.session.commit()` with appropriate service methods
4. Replace relationship access (`user.settings`) with service methods (`user_service.get_with_settings`)
5. Update any code that used SQLAlchemy-specific features (like `Query.join()`) to use the new service methods

## Environment Variables

The following environment variables are used:

- `DB_USER`: Database username (default: `postgres`)
- `DB_PASSWORD`: Database password (default: `postgres`)
- `DB_HOST`: Database host (default: `localhost`)
- `DB_PORT`: Database port (default: `5432`)
- `DB_NAME`: Database name (default: `recruiting`)

## Contributing

When adding new functionality:

1. Add appropriate models to the `models/` directory
2. Add corresponding services to the `services/` directory
3. Update the database schema in `migrations/schema.sql`
4. Document new methods and models
5. Add tests for new functionality
