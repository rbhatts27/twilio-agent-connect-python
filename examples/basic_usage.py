#!/usr/bin/env python3
"""
Basic usage example for Twilio Agentic Framework.

This example demonstrates the basic functionality of the taf package.
"""

from taf import __version__, hello


def main():
    """Main example function."""
    print("Twilio Agentic Framework Examples")
    print("=" * 40)
    print()

    # Display version information
    print(f"TAF Version: {__version__}")
    print()

    # Basic hello function usage
    print("Basic Usage:")
    message = hello()
    print(f"Message: {message}")
    print()

    # Type checking demonstration
    print("Type Information:")
    print(f"Message type: {type(message)}")
    print(f"Message length: {len(message)}")
    print()


if __name__ == "__main__":
    main()
