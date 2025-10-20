# Custom Instructions for GitHub Copilot

This file contains custom instructions for GitHub Copilot to enhance its code suggestions and completions. The instructions are designed to help Copilot better understand the context of the project and provide more relevant and accurate code snippets.

## General Guidelines
- Indentation: Use 2 spaces for indentation.
- Comment Style: Use `//` for single-line comments and `/* ... */` for multi-line comments.
- Naming Conventions: Use camelCase for variables and functions, PascalCase for classes, and UPPER_SNAKE_CASE for constants.
- File Structure: Follow the project's file structure and organization.
- Code Style: Adhere to the project's coding style guidelines, including spacing, brackets, and semicolons.
- Language-Specific Guidelines: Follow best practices and conventions for the specific programming language used in the project.
- Context Awareness: Consider the surrounding code and project context when suggesting code snippets.
- Error Handling: Include appropriate error handling and validation in code suggestions.
- Documentation: Provide clear and concise documentation for functions, classes, and modules only in english.
- All code files will be lowercase with words separated by hyphens.


# Python Coding Conventions

## Python Instructions

- Write clear and concise comments for each function.
- Ensure functions have descriptive names and include type hints.
- Provide docstrings following PEP 257 conventions.
- Use the `typing` module for type annotations (e.g., `List[str]`, `Dict[str, int]`).
- Break down complex functions into smaller, more manageable functions.

## General Instructions

- Always prioritize readability and clarity.
- For algorithm-related code, include explanations of the approach used.
- Write code with good maintainability practices, including comments on why certain design decisions were made.
- Handle edge cases and write clear exception handling.
- For libraries or external dependencies, mention their usage and purpose in comments.
- Use consistent naming conventions and follow language-specific best practices.
- Write concise, efficient, and idiomatic code that is also easily understandable.

## Code Style and Formatting

- Follow the **PEP 8** style guide for Python.
- Maintain proper indentation (use 4 spaces for each level of indentation).
- Ensure lines do not exceed 79 characters.
- Place function and class docstrings immediately after the `def` or `class` keyword.
- Use blank lines to separate functions, classes, and code blocks where appropriate.

## Edge Cases and Testing

- Always include test cases for critical paths of the application.
- Account for common edge cases like empty inputs, invalid data types, and large datasets.
- Include comments for edge cases and the expected behavior in those cases.
- Write unit tests for functions and document them with docstrings explaining the test cases.
- For Testing terminal commands, use the docker container named "ubiquiti-automation_dev" with the command `docker exec -it ubiquiti-automation bash`.

## Example of Proper Documentation

```python
def calculate_area(radius: float) -> float:
    """
    Calculate the area of a circle given the radius.
    
    Parameters:
    radius (float): The radius of the circle.
    
    Returns:
    float: The area of the circle, calculated as π * radius^2.
    """
    import math
    return math.pi * radius ** 2
```