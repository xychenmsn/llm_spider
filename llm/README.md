# LLM Wrapper

This module provides a wrapper around the LLMClient that adds several useful features:

1. **Persistent System Prompt**: Always includes a system prompt with every LLM call
2. **Chat History Management**: Maintains conversation history and intelligently includes as much as possible within token limits
3. **Focus Mode**: Ensures user queries align with the system prompt's purpose

## Installation

Make sure you have the required dependencies:

```bash
pip install openai python-dotenv
```

## Usage

### Basic Usage

```python
from llm.llm_wrapper import LLMWrapper

# Define your system prompt
system_prompt = """
You are a helpful AI assistant specialized in answering questions about Python programming.
Your primary goal is to provide accurate, concise, and helpful information about Python.
If asked about topics unrelated to Python programming, politely redirect the conversation
back to Python-related topics.
"""

# Create the wrapper with focus mode and function schemas
function_schemas = [
    {
        "type": "function",
        "function": {
            "name": "search_python_docs",
            "description": "Search the Python documentation for information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

# Create the wrapper with focus mode enabled
wrapper = LLMWrapper(
    system_prompt=system_prompt,
    focus_mode=True,  # Enable focus mode by default
    function_schemas=function_schemas  # Set function schemas in constructor
)

# Chat with the LLM
response = wrapper.chat("How do I use list comprehensions in Python?")

# For non-streaming responses
print(response.content)

# For streaming responses
for chunk in wrapper.chat("What are Python decorators?", stream=True):
    if isinstance(chunk, str):
        print(chunk, end="", flush=True)
```

### Focus Mode

Focus mode wraps user input in a JSON structure with instructions to ensure the LLM stays on topic:

```python
# Create wrapper with focus mode enabled by default
wrapper = LLMWrapper(
    system_prompt="Your system prompt here",
    focus_mode=True
)

# Or enable/disable for specific requests
response = wrapper.chat(
    "Tell me about the weather in Paris", 
    focus_mode=True  # Override the default setting
)
# The LLM will politely decline and remind the user of its purpose
```

### Managing History

The wrapper automatically manages chat history, but you can also:

```python
# Clear history
wrapper.clear_history()

# Get current history
history = wrapper.get_history()
```

### Advanced Configuration

```python
from llm.llm_client import LLMClient

# Create with custom parameters
wrapper = LLMWrapper(
    system_prompt="Your system prompt here",
    llm_client=LLMClient(api_key="your_api_key"),  # Optional custom client
    max_history_tokens=3000,  # Default is 4000
    model="gpt-3.5-turbo"  # Default is "gpt-4-turbo-preview"
)

# Use with function calling
function_schemas = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather in a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    }
                },
                "required": ["location"]
            }
        }
    }
]

response = wrapper.chat(
    "What's the weather in San Francisco?",
    function_schemas=function_schemas
)
```

## Example

See the `examples/llm_wrapper_example.py` file for a complete example of how to use the LLMWrapper class.

## How It Works

### Token Management

The wrapper uses a simple token estimation algorithm to determine how much of the chat history can be included in each request. It prioritizes:

1. The system prompt (always included)
2. The current user input
3. Recent chat history, with newer messages having higher priority

### Focus Mode

When focus mode is enabled, the user input is wrapped in a JSON structure:

```json
{
  "user_input": "The original user input",
  "instructions": "If this input aligns with your system instructions, respond normally. If it doesn't, politely decline and remind the user of your purpose."
}
```

This helps the LLM stay on topic and adhere to the system prompt's purpose. 