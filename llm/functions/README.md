# LLM Spider Functions

This directory contains the functions that can be called by the LLM. Each function is defined in its own file and automatically discovered and registered by the `FunctionManager`.

## Directory Structure

- `__init__.py` - Imports and exports all functions
- `fetch_webpage.py` - Function to fetch the HTML content of a webpage
- `parse_with_parser.py` - Function to parse a webpage using an LLM-generated parser
- `template.py` - Template for creating new functions (excluded from automatic discovery)

## How to Create a New Function

1. Copy the `template.py` file and rename it to match your function name (e.g., `my_function.py`)
2. Modify the class name, function name, description, parameters, and required parameters
3. Implement the `execute` method to handle the function logic
4. Import the function in `__init__.py` and add it to the `__all__` list

The new function will be automatically discovered and registered by the `FunctionManager` as long as:
- It's in the `llm/functions` directory
- It's not named `template.py`, `__init__.py`, or `base.py`
- It defines a class that inherits from `Function`
- The class has a non-empty `name` attribute

Example:

```python
# my_function.py
from llm.function import Function

class MyFunction(Function):
    name = "my_function"
    description = "Description of my function"
    parameters = {
        "param1": {
            "type": "string",
            "description": "Description of parameter 1"
        }
    }
    required_parameters = {"param1"}
    
    def execute(self, args):
        param1 = args.get("param1", "")
        if not param1:
            return {"error": "param1 is required"}
        
        # Implement function logic
        return {"result": f"Executed my_function with param1={param1}"}
```

Then in `__init__.py`:

```python
from llm.function import Function

from .fetch_webpage import FetchWebpage
from .parse_with_parser import ParseWithParser
from .my_function import MyFunction  # Import your new function

__all__ = [
    'Function',
    'FetchWebpage',
    'ParseWithParser',
    'MyFunction',  # Add your new function to the exports
]
```

## How to Use Functions

Functions are automatically discovered and registered by the `FunctionManager` when they are imported. To use a function, you need to:

1. Import the FunctionManager from llm.function_manager
2. Create a `FunctionManager` instance with any context needed for execution
3. Call the `execute_function` method with the function name and arguments

Example:

```python
from llm.function_manager import FunctionManager

# Create a function manager with context
manager = FunctionManager(context_object=my_context)

# Execute a function
result = manager.execute_function("my_function", {"param1": "value1"})
```

## How to Get Function Schemas

To get the schemas for all registered functions, use the `get_function_schemas` function:

```python
from llm.function_manager import get_function_schemas

# Get all function schemas
schemas = get_function_schemas()
```

This is useful when setting up the LLM client to use function calling. 