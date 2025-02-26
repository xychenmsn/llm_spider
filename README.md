# LLM Spider

LLM Spider is a universal web page parser that can extract structured data from any URL. Given a URL, if a parser already exists for that URL pattern, LLM Spider will automatically parse the content. If no parser exists, users can create a new parser through an intuitive LLM-powered chat interface.

## Features

- **Universal Web Page Parsing**: Parse any web page with the appropriate parser
- **LLM-Assisted Parser Creation**: Create new parsers through natural language conversation with an AI assistant
- **Pattern Matching**: Automatically match URLs to existing parsers using regex patterns
- **Extensible Architecture**: Easy to add new parser types and extend functionality
- **Modern UI**: Clean and intuitive interface built with PySide6 (Qt for Python)
- **Database Storage**: Store and manage URL parsers with SQLAlchemy

## Project Structure

```
llm_spider/
├── app.py                     # Main application entry point
├── parser_designer.py         # LLM-assisted parser creation interface
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
│   ├── test_db_operations.py
│   └── test_openai_api.py     # OpenAI API test script
├── utils/                     # Utility modules
│   └── __init__.py
└── README.md                  # Main README file
```

## Setup

### Prerequisites

- Python 3.8 or higher
- SQLite (or another database supported by SQLAlchemy)
- OpenAI API key (for LLM-assisted parser creation)

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

3. Set up your environment variables by creating a `.env` file:

```
# Database Configuration
DATABASE_URL=sqlite:///db/llm_spider.db

# LLM Configuration
OPENAI_API_KEY=your_openai_api_key_here
OLLAMA_BASE_URL=http://localhost:11434

# Application Settings
DEBUG=True
LOG_LEVEL=INFO

# UI Settings
DEFAULT_THEME=dark_teal.xml
```

4. Initialize the database:

```bash
python db/init_db.py
```

5. Run the migrations:

```bash
alembic upgrade head
```

## Usage

### Running the Application

To start the application, run:

```bash
python app.py
```

This will open the main LLM Spider interface where you can:
- Enter URLs to parse
- View and manage existing parsers
- Create new parsers for unsupported URL patterns

### Creating a New Parser

When you encounter a URL that doesn't match any existing parser, you can create a new one:

1. Enter the URL in the main application
2. When prompted that no parser exists, select "Create New Parser"
3. The Parser Designer will open with an LLM-powered chat interface
4. Describe what data you want to extract from the URL
5. The AI assistant will help you design a parser through conversation
6. Save the parser when you're satisfied with the design

### Using Existing Parsers

To parse a URL with an existing parser:

1. Enter the URL in the main application
2. If a matching parser is found, it will be automatically used
3. The parsed data will be displayed in the application

## How It Works

LLM Spider uses a combination of:

1. **Regex Pattern Matching**: To identify which parser to use for a given URL
2. **Large Language Models**: To assist in creating new parsers through natural conversation
3. **Database Storage**: To store and retrieve parser configurations
4. **PySide6 UI**: To provide a user-friendly interface

## Database

The application uses SQLAlchemy and Alembic for database operations and migrations. The main model is `URLParser` which stores:

- Name and description of the parser
- URL pattern (regex) to match URLs
- Parser implementation details
- Metadata and chat configuration

## Testing

Test scripts are available in the `playground` directory:

```bash
# Test database operations
python playground/test_db_client.py
python playground/test_db_operations.py

# Test OpenAI API connection
python playground/test_openai_api.py
```

## License

*Coming soon*

## Contributing

*Coming soon* 