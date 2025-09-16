# Twilio Agentic Framework

A Python framework for building agentic applications with Twilio.

## Installation

Install directly from this Git repository:

```bash
pip install git+https://github.com/twilio-internal/twilio-agentic-framework-python.git
```

For development:

```bash
git clone https://github.com/twilio-internal/twilio-agentic-framework-python.git
cd twilio-agentic-framework-python
poetry install
```

Or for editable pip install:

```bash
git clone https://github.com/twilio-internal/twilio-agentic-framework-python.git
cd twilio-agentic-framework-python
pip install -e .
```

## Usage

```python
from taf import hello

print(hello())  # Output: Hello from Twilio Agentic Framework!
```

## Development

1. Clone the repository
2. Install in development mode: `pip install -e .`
3. Make changes and test locally

## License

MIT License