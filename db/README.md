# Database Module for LLM Spider

This directory contains the database module for the LLM Spider application. It provides a robust database client and models for storing and retrieving URL parsers.

## Overview

The database module consists of the following components:

- **Models**: SQLAlchemy models for the database tables
- **DBClient**: A robust database client that handles detached objects properly
- **DB Operations**: Utility functions for common database operations specific to URL parsers
- **Migrations**: Alembic migrations for database schema changes

## Setup

### 1. Initialize the Database

To initialize the database, run:

```bash
python db/init_db.py
```

This will create the database tables and populate them with initial data.

### 2. Run Migrations

To run database migrations, use Alembic:

```bash
alembic upgrade head
```

This will apply all pending migrations to the database.

## Usage

### Using the DBClient

The `DBClient` class provides a robust interface for database operations. It handles detached objects properly and provides a clean API for common operations.

```python
from db.db_client import db_client
from db.models import URLParser

# Get all URL parsers
parsers = db_client.get_all(URLParser)

# Get a URL parser by ID
parser = db_client.get_by_id(URLParser, 1)

# Create a new URL parser
new_parser = URLParser(
    name="Example Parser",
    url_pattern=r"https://example\.com/.*",
    parser="example_parser",
    meta_data={"key": "value"},
    chat_data={"system_prompt": "You are analyzing an example."}
)
created_parser = db_client.create(new_parser)

# Update a URL parser
updated_parser = db_client.update(URLParser, 1, url_pattern=r"https://example\.com/new/.*")

# Delete a URL parser
success = db_client.delete(URLParser, 1)
```

### Using the Database Operations Utilities

The `db.db_operations` module provides utility functions for common database operations specific to URL parsers.

```python
from db.db_operations import (
    get_all_url_parsers,
    get_url_parser_by_id,
    get_url_parser_by_name,
    find_parser_for_url,
    create_url_parser,
    update_url_parser,
    delete_url_parser
)

# Get all URL parsers
parsers = get_all_url_parsers()

# Get a URL parser by name
parser = get_url_parser_by_name("GitHub Repository")

# Find a parser for a URL
parser = find_parser_for_url("https://github.com/username/repo")

# Create a new URL parser
new_parser = create_url_parser(
    name="Example Parser",
    url_pattern=r"https://example\.com/.*",
    parser="example_parser",
    meta_data={"key": "value"},
    chat_data={"system_prompt": "You are analyzing an example."}
)

# Update a URL parser
updated_parser = update_url_parser(
    parser_id=1,
    url_pattern=r"https://example\.com/new/.*",
    meta_data={"key": "new_value"}
)

# Delete a URL parser
success = delete_url_parser(1)
```

## Models

### URLParser

The `URLParser` model represents a URL parser in the database. It has the following fields:

- `id`: Integer, primary key
- `name`: String, unique
- `url_pattern`: String, regex pattern for matching URLs
- `parser`: String, name of the parser function
- `meta_data`: JSON, metadata for the parser
- `chat_data`: JSON, chat data for the parser
- `created_at`: DateTime, when the parser was created
- `updated_at`: DateTime, when the parser was last updated

## Migrations

Database migrations are managed using Alembic. The migrations directory contains:

- `env.py`: Sets up the Alembic migration environment
- `script.py.mako`: Template for generating migration scripts
- `versions/`: Directory containing migration scripts

To create a new migration, run:

```bash
alembic revision --autogenerate -m "Description of the migration"
```

To apply migrations, run:

```bash
alembic upgrade head
```

## Testing

Test scripts are available in the `playground` directory:

- `test_db_client.py`: Tests for the DBClient class
- `test_db_operations.py`: Tests for the database operations utility functions

To run the tests, use:

```bash
python playground/test_db_client.py
python playground/test_db_operations.py
``` 