#!/usr/bin/env python3
"""
Manual Test Script for Twilio Agentic Framework

Test TAF processing with various webhook scenarios without needing a server.
Includes sample payloads and edge cases for comprehensive testing.
"""

import json
import os
import sys
from typing import Any, Dict

# Add parent directory to path to import taf
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from taf import TAF, ModelProvider, TAFConfig

# Sample webhook payloads for testing
SAMPLE_WEBHOOKS = {
    "basic_message": {
        "EventType": "onMessageAdded",
        "ConversationSid": "CHd151e6bcbe3643979a3f41f6d0da3b24",
        "Body": "Hello, I need help with my order",
        "Author": "+12162622233",
    },
    "complete_twilio_webhook": {
        "MessagingServiceSid": "MG3675a614bcfcfb1921727b0138617cdf",
        "EventType": "onMessageAdded",
        "Attributes": "{}",
        "DateCreated": "2025-09-17T22:23:11.350Z",
        "Index": "8",
        "ChatServiceSid": "IS21622ffdbc4947a4a0c1abaa77dfd024",
        "MessageSid": "IM40cb38d6045f4da195651b3e29cca1dc",
        "AccountSid": "ACa0cec02523bd4da792b4bff42b77fc22",
        "Source": "SMS",
        "RetryCount": "0",
        "Author": "+12162622233",
        "ParticipantSid": "MB723da60623f74438acee5baafbd438f0",
        "Body": "Hi, I'm having trouble with my account login. Can you help me reset my password?",
        "ConversationSid": "CHd151e6bcbe3643979a3f41f6d0da3b24",
    },
    "empty_message": {
        "EventType": "onMessageAdded",
        "ConversationSid": "CHd151e6bcbe3643979a3f41f6d0da3b24",
        "Body": "",
        "Author": "+12162622233",
    },
    "whitespace_message": {
        "EventType": "onMessageAdded",
        "ConversationSid": "CHd151e6bcbe3643979a3f41f6d0da3b24",
        "Body": "   \n  \t  ",
        "Author": "+12162622233",
    },
    "non_message_event": {
        "EventType": "onParticipantAdded",
        "ConversationSid": "CHd151e6bcbe3643979a3f41f6d0da3b24",
        "ParticipantSid": "MB723da60623f74438acee5baafbd438f0",
        "Author": "+12162622233",
    },
    "urgent_customer_message": {
        "EventType": "onMessageAdded",
        "ConversationSid": "CHd151e6bcbe3643979a3f41f6d0da3b24",
        "Body": "URGENT: My payment failed and I need immediate assistance!",
        "Author": "+12162622233",
    },
    "emoji_message": {
        "EventType": "onMessageAdded",
        "ConversationSid": "CHd151e6bcbe3643979a3f41f6d0da3b24",
        "Body": "Hello! 👋 Can you help me? 😊",
        "Author": "+12162622233",
    },
    "long_message": {
        "EventType": "onMessageAdded",
        "ConversationSid": "CHd151e6bcbe3643979a3f41f6d0da3b24",
        "Body": "I've been trying to resolve this issue for hours. " * 20,
        "Author": "+12162622233",
    },
}

INVALID_WEBHOOKS = {
    "missing_required_fields": {
        "EventType": "onMessageAdded",
        # Missing ConversationSid, Body, Author
    },
    "invalid_event_type": {
        "EventType": "",
        "ConversationSid": "CHd151e6bcbe3643979a3f41f6d0da3b24",
        "Body": "Hello",
        "Author": "+12162622233",
    },
    "completely_empty": {},
}


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def print_subheader(title: str):
    """Print a formatted subheader."""
    print(f"\n--- {title} ---")


def test_webhook(taf: TAF, name: str, webhook: Dict[str, Any]) -> bool:
    """Test a single webhook and return success status."""
    try:
        result = taf.process_message(webhook)

        print(f"✅ {name}")
        print(f"   Should process: {result['processing']['should_process']}")
        print(f"   Event type: {result['event']['type']}")
        print(
            f"   Message: '{result['event']['body'][:50]}{'...' if len(result['event']['body']) > 50 else ''}'"
        )

        return True

    except Exception as e:
        print(f"❌ {name}")
        print(f"   Error: {str(e)}")
        return False


def test_configuration():
    """Test different TAF configurations."""
    print_header("Configuration Testing")

    # Test valid configurations
    print_subheader("Valid Configurations")

    valid_configs = [
        {"model_provider": "openai"},
        TAFConfig(model_provider=ModelProvider.OPENAI),
    ]

    for i, config in enumerate(valid_configs):
        try:
            taf = TAF(config)
            print(f"✅ Config {i+1}: {type(config).__name__}")
            print(f"   Provider: {taf.config.model_provider}")
        except Exception as e:
            print(f"❌ Config {i+1}: {str(e)}")

    # Test invalid configurations
    print_subheader("Invalid Configurations")

    invalid_configs = [
        {"model_provider": "invalid_provider"},
        "not_a_dict",
        123,
        None,
    ]

    for i, config in enumerate(invalid_configs):
        try:
            taf = TAF(config)
            print(f"❌ Invalid config {i+1}: Should have failed but didn't!")
        except Exception as e:
            print(f"✅ Invalid config {i+1}: Correctly rejected - {str(e)}")


def test_valid_webhooks():
    """Test valid webhook scenarios."""
    print_header("Valid Webhook Testing")

    # Initialize TAF
    taf = TAF({"model_provider": "openai"})

    success_count = 0
    total_count = len(SAMPLE_WEBHOOKS)

    for name, webhook in SAMPLE_WEBHOOKS.items():
        if test_webhook(taf, name, webhook):
            success_count += 1

    print_subheader("Summary")
    print(f"Passed: {success_count}/{total_count} tests")

    return success_count == total_count


def test_invalid_webhooks():
    """Test invalid webhook scenarios."""
    print_header("Invalid Webhook Testing")

    taf = TAF({"model_provider": "openai"})

    for name, webhook in INVALID_WEBHOOKS.items():
        print_subheader(f"Testing {name}")
        try:
            result = taf.process_message(webhook)
            print(f"❌ {name}: Should have failed but got result: {result}")
        except Exception as e:
            print(f"✅ {name}: Correctly rejected - {str(e)}")


def test_batch_processing():
    """Test processing multiple webhooks in sequence."""
    print_header("Batch Processing Test")

    taf = TAF({"model_provider": "openai"})

    # Process all valid webhooks in sequence
    results = []
    for name, webhook in SAMPLE_WEBHOOKS.items():
        try:
            result = taf.process_message(webhook)
            results.append((name, result, True))
        except Exception as e:
            results.append((name, str(e), False))

    # Analyze results
    successful = [r for r in results if r[2]]
    processed = [r for r in successful if r[1] is not None]

    print(f"Total webhooks: {len(results)}")
    print(f"Successfully parsed: {len(successful)}")
    print(f"Processed by AI: {len(processed)}")

    print_subheader("Processing Decisions")
    for name, result, success in results:
        if success:
            status = "PROCESS" if result is not None else "SKIP"
            print(f"  {name}: {status}")
        else:
            print(f"  {name}: ERROR - {result}")


def performance_test():
    """Test processing performance with multiple webhooks."""
    print_header("Performance Test")

    import time

    taf = TAF({"model_provider": "openai"})
    webhook = SAMPLE_WEBHOOKS["basic_message"]

    # Test processing speed
    iterations = 1000

    start_time = time.time()
    for _ in range(iterations):
        taf.process_message(webhook)
    end_time = time.time()

    total_time = end_time - start_time
    avg_time = total_time / iterations

    print(f"Processed {iterations} webhooks in {total_time:.4f} seconds")
    print(f"Average time per webhook: {avg_time*1000:.4f} ms")
    print(f"Webhooks per second: {iterations/total_time:.2f}")


def interactive_test():
    """Interactive testing mode."""
    print_header("Interactive Testing Mode")

    taf = TAF({"model_provider": "openai"})

    print("Enter webhook data as JSON (or 'quit' to exit):")
    print(
        "Example: {'EventType': 'onMessageAdded', 'ConversationSid': 'CH123', 'Body': 'Hello', 'Author': '+1234567890'}"
    )

    while True:
        try:
            user_input = input("\n> ").strip()

            if user_input.lower() in ["quit", "exit", "q"]:
                break

            if user_input.startswith("sample:"):
                # Use predefined sample
                sample_name = user_input[7:].strip()
                if sample_name in SAMPLE_WEBHOOKS:
                    webhook_data = SAMPLE_WEBHOOKS[sample_name]
                    print(f"Using sample: {sample_name}")
                else:
                    print(
                        f"Unknown sample. Available: {', '.join(SAMPLE_WEBHOOKS.keys())}"
                    )
                    continue
            else:
                # Parse user JSON
                webhook_data = json.loads(user_input)

            result = taf.process_message(webhook_data)
            print("\nResult:")
            print(json.dumps(result, indent=2))

        except json.JSONDecodeError:
            print("Invalid JSON. Please try again.")
        except Exception as e:
            print(f"Error: {str(e)}")


def main():
    """Run all manual tests."""
    print_header("Twilio Agentic Framework - Manual Testing")

    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        interactive_test()
        return

    # Run all test suites
    test_configuration()
    test_valid_webhooks()
    test_invalid_webhooks()
    test_batch_processing()
    performance_test()

    print_header("Testing Complete")
    print("For interactive testing, run: python manual_test.py interactive")
    print(f"Available samples: {', '.join(SAMPLE_WEBHOOKS.keys())}")
    print("Use 'sample:basic_message' format in interactive mode")


if __name__ == "__main__":
    main()
