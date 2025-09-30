# Twilio Agentic Framework (TAF)

## Overview

Twilio Agentic Framework (TAF) is a powerful Python library designed to simplify the development of intelligent,
context-aware applications using Twilio's communication technologies.

---

# TAF Usage

This section is for end users who want to **install and use TAF** in their projects.

## Requirements

- **Python Versions**: 3.8, 3.9, 3.10, 3.11, 3.12
- **Recommended**: Python 3.9 or higher

---

## Installation

### Option 1: Install from GitHub

```bash
pip install git+https://github.com/twilio-internal/twilio-agentic-framework-python.git
````

### Option 2: Local Development Installation (Optional)

```bash
git clone https://github.com/twilio-internal/twilio-agentic-framework-python.git
cd twilio-agentic-framework-python

pip install -e .
```

### Option 3: Using Poetry (Optional)

```bash
pip install poetry
git clone https://github.com/twilio-internal/twilio-agentic-framework-python.git
cd twilio-agentic-framework-python

poetry install
```

---

## Configuration

### Environment Variables

Copy the example file and fill in your credentials:

```bash
cp .env.example .env
```

### Programmatic Configuration

```python
from taf import TAF, TAFConfig

config = TAFConfig(
    twilio_account_sid="your_account_sid",
    memora_auth_token="your_memora_auth_token",
    memora_base_url="https://memory.twilio.com/v1",
    maestro_base_url="https://maestro.twilio.com/v1"
)

taf = TAF(config)
```

---

# TAF Development / Contribution

This section is for developers who want to **contribute or run TAF locally**.

## Setting Up Your Local Environment

### Option 1: Using `venv` (Recommended)

```bash
# Create a virtual environment
python3 -m venv env

# Activate the virtual environment
# macOS/Linux:
source env/bin/activate
# Windows:
.\env\Scripts\activate

# Verify Python version
python --version

# Deactivate when done
deactivate
```

### Option 2: Using `uv` (Faster for Development, Optional)

[uv](https://astral.sh/uv) is a fast tool for managing Python virtual environments and dependencies.

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
# or on macOS with Homebrew
brew install uv

# Create uv-managed virtual environment
uv venv

# Install dependencies from Poetry's lock file
uv run pip install -r <(poetry export -f requirements.txt --without-hashes)

# Run project or tests
uv run python -m taf.main
uv run pytest
```

> Note: `uv.lock` generated locally is optional and does not need to be committed. Poetry remains the source of truth
> for dependencies.

---

## Installing Development Dependencies

If using Poetry:

```bash
poetry install --with dev
```

Or manually with pip:

```bash
pip install -e .
pip install pytest pytest-cov black isort mypy types-requests
```

---

## Running Tests

```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run a specific test module
pytest tests/test_specific_module.py
```

---

## Code Quality Checks

```bash
# Format code
black .

# Sort imports
isort .

# Type checking
mypy .
```

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push to the branch
5. Open a Pull Request

---

## Troubleshooting

* Verify Python version: `python --version`
* Ensure virtual environment is activated
* Check all required environment variables
* Verify dependencies are correctly installed

---

## License

MIT License - See LICENSE file for details

---

## Support

For issues, please file a GitHub issue in the repository.
