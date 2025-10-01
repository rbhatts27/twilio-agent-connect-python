# Twilio Agentic Framework (TAF)

Twilio Agentic Framework (TAF) is a powerful Python library designed to simplify the development of intelligent,
context-aware applications using Twilio's communication technologies.

> [!NOTE]
> Looking for the JavaScript/TypeScript version? Check out [TAF SDK JS/TS](https://github.com/twilio-internal/twilio-agentic-framework-typescript).

Explore the [examples](examples) directory to see the SDK in action.


## Get started

To get started, set up your Python environment (Python 3.9 or newer required), and then install TAF SDK package.

### venv

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install git+https://github.com/twilio-internal/twilio-agentic-framework-python.git
```

### uv

If you're familiar with [uv](https://docs.astral.sh/uv/), using the tool would be even similar:

```bash
uv init
uv add git+https://github.com/twilio-internal/twilio-agentic-framework-python.git
```

## Example

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

0. Ensure you have [`uv`](https://docs.astral.sh/uv/) installed.

```bash
uv --version
```

1. Install dependencies

```bash
make sync
```

2. (After making changes) lint/test

```
make format # run tests linter and typechecker
```
