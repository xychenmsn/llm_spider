# LLM Spider

LLM Spider is a Python-based chat application that processes URLs and generates insights using Large Language Models (LLMs). It can parse different types of URLs (GitHub repositories, Medium articles, Stack Overflow questions, etc.) and provide relevant information and analysis.

## Features

- URL parsing and analysis
- Integration with Large Language Models
- Database storage for URL parsers
- Extensible architecture for adding new URL parsers
- Clean and modern UI

## Project Structure

```
llm_spider/
├── alembic.ini                # Alembic configuration
├── db/                        # Database module
│   ├── __init__.py
│   ├── db_client.py           # Database client
│   ├── db_operations.py       # Database operations utilities
│   ├── init_db.py             # Database initialization script
│   ├── models.py              # SQLAlchemy models
│   └── README.md              # Database module documentation
├── migrations/                # Alembic migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/              # Migration versions
├── playground/                # Test scripts
│   ├── test_db.py
│   ├── test_db_client.py
│   └── test_db_operations.py
├── utils/                     # Utility modules
│   └── __init__.py
└── README.md                  # Main README file
```

## Setup

### Prerequisites

- Python 3.8 or higher
- SQLite (or another database supported by SQLAlchemy)

### Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/llm_spider.git
cd llm_spider
```

2. Install the dependencies:

```bash
pip install -r requirements.txt
```

3. Initialize the database:

```bash
python db/init_db.py
```

4. Run the migrations:

```bash
alembic upgrade head
```

## Usage

### Running the Application

*Coming soon*

### Adding a New URL Parser

To add a new URL parser, you need to:

1. Create a new parser function in the appropriate module
2. Add a new URL parser to the database:

```python
from db.db_operations import create_url_parser

create_url_parser(
    name="New Parser",
    url_pattern=r"https://example\.com/.*",
    parser="new_parser",
    meta_data={
        "site": "example.com",
        "type": "example"
    },
    chat_data={
        "system_prompt": "You are analyzing an example.",
        "user_prompt_template": "Please analyze this example: {url}"
    }
)
```

## Database

The application uses SQLAlchemy and Alembic for database operations and migrations. See the [Database README](db/README.md) for more information.

## Testing

Test scripts are available in the `playground` directory:

```bash
python playground/test_db_client.py
python playground/test_db_operations.py
```

## License

*Coming soon*

## Contributing

*Coming soon* 