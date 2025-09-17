import pytest

from taf import __version__, hello


def test_hello():
    """Test that hello function returns expected message."""
    result = hello()
    assert result == "Hello from Twilio Agentic Framework!"
    assert isinstance(result, str)


def test_version():
    """Test that version is available and is a string."""
    assert isinstance(__version__, str)
    assert __version__ == "0.1.0"


def test_hello_no_args():
    """Test that hello function works without arguments."""
    result = hello()
    assert result is not None
    assert len(result) > 0
