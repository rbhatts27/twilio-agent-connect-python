# Examples

This directory contains usage examples for the Twilio Agentic Framework.

## Running Examples

Make sure you have the package installed:

```bash
# Install in development mode
pip install -e .

# Or install with poetry
poetry install
```

## Available Examples

### basic_usage.py
Demonstrates the basic functionality of the `taf` package:

```bash
python examples/basic_usage.py
```

**What it shows:**
- Package version information
- Basic `hello()` function usage
- Type checking and validation

## Expected Output

```
Twilio Agentic Framework Examples
========================================

TAF Version: 0.1.0

Basic Usage:
Message: Hello from Twilio Agentic Framework!

Type Information:
Message type: <class 'str'>
Message length: 35
```

## Adding New Examples

When adding new examples:

1. Create a new `.py` file in this directory
2. Include docstrings explaining the example
3. Add the example to this README
4. Test the example works with both `pip install -e .` and `poetry run python examples/<file>.py`