#!/usr/bin/env python3
"""
SMS Server for Twilio Agentic Framework

Example demonstrating SMSChannel with FastAPI server for webhook endpoint.
"""

import os
import sys
from typing import Optional

import openai
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path to import taf
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from taf import TAF, TAFConfig, get_logger
from taf.channels.sms import SMSChannel
from taf.models.memory import MemoryRetrievalResponse
from taf.models.session import ConversationSession

# Initialize logger
logger = get_logger(__name__)

# Global variables
sms_channel: SMSChannel
system_prompt = "You're a helpful assistant that helps users via text messages."

# User-managed conversation history
# Key: conversation_id, Value: list of messages
conversation_messages: dict[str, list[ChatCompletionMessageParam]] = {}


async def handle_message_ready(
    user_message: str,
    context: ConversationSession,
    memory_response: Optional[MemoryRetrievalResponse],
) -> None:
    """
    Callback invoked when a message is ready to be processed.

    Processes user message with OpenAI, using retrieved memories for context
    and maintaining conversation history for coherent multi-turn interactions.
    """
    logger.info(f"Processing message for conversation {context.conversation_id}")

    if memory_response:
        logger.info(
            f"Retrieved memories: {len(memory_response.observations)} observations, "
            f"{len(memory_response.summaries)} summaries, {len(memory_response.sessions)} sessions"
        )

    # Initialize conversation history with system message
    conv_id = context.conversation_id
    if conv_id not in conversation_messages:
        system_msg: ChatCompletionSystemMessageParam = {"role": "system", "content": system_prompt}
        conversation_messages[conv_id] = [system_msg]

        # Add profile traits as context if available
        if context.profile:
            traits = context.profile.traits
            logger.info(f"Profile traits available: {list(traits.keys())}")

            # Build a personalized context message with profile information
            profile_context_parts = []
            if "Contact" in traits:
                contact = traits["Contact"]
                if "firstName" in contact:
                    profile_context_parts.append(f"User's name: {contact['firstName']}")
                if "lastName" in contact:
                    profile_context_parts.append(f"Last name: {contact['lastName']}")
                if "address" in contact:
                    address = contact["address"]
                    city = address.get("city", "")
                    state = address.get("state", "")
                    if city and state:
                        profile_context_parts.append(f"Location: {city}, {state}")

            if "Preferences" in traits:
                prefs = traits["Preferences"]
                if "language" in prefs:
                    profile_context_parts.append(f"Preferred language: {prefs['language']}")

            if profile_context_parts:
                profile_context = "User Profile Information:\n" + "\n".join(
                    f"- {part}" for part in profile_context_parts
                )
                context_msg: ChatCompletionSystemMessageParam = {
                    "role": "system",
                    "content": profile_context,
                }
                conversation_messages[conv_id].append(context_msg)
                logger.info(f"Added profile context to conversation: {profile_context}")

    # Add user message to history
    user_msg: ChatCompletionUserMessageParam = {"role": "user", "content": user_message}
    conversation_messages[conv_id].append(user_msg)

    # Generate response with OpenAI
    client = openai.AsyncOpenAI(api_key=os.environ.get("TWILIO_TAF_OPENAI_API_KEY"))
    completion = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=conversation_messages[conv_id],
    )

    response = completion.choices[0].message.content

    logger.info("Response generated: %s", response)

    # Send response and update history
    if response:
        assistant_msg: ChatCompletionAssistantMessageParam = {
            "role": "assistant",
            "content": response,
        }
        conversation_messages[conv_id].append(assistant_msg)

        await sms_channel.send_response(context.conversation_id, response, role="assistant")


if __name__ == "__main__":
    # Initialize TAF - automatically loads all configuration from environment variables
    # Required env vars:
    #   - TWILIO_TAF_ENVIRONMENT (dev, stage, or prod)
    #   - TWILIO_TAF_CONVERSATION_SERVICE_SID
    #   - TWILIO_TAF_ACCOUNT_SID
    #   - TWILIO_TAF_AUTH_TOKEN
    #   - TWILIO_TAF_PHONE_NUMBER
    # Optional env vars:
    #   - TWILIO_TAF_LOG_LEVEL (defaults to INFO)
    #   - TWILIO_TAF_MEMORY_STORE_ID, TWILIO_TAF_MEMORY_API_KEY, TWILIO_TAF_MEMORY_API_TOKEN (for Twilio Memory)
    #   - TWILIO_TAF_TRAIT_GROUPS (comma-separated, e.g., "Contact,Preferences")
    taf = TAF(config=TAFConfig.from_env())

    # Register callback for message ready
    taf.on_message_ready(handle_message_ready)

    # Initialize channel
    sms_channel = SMSChannel(taf)

    # Create FastAPI app
    app = FastAPI(title="TAF SMS Server")

    @app.post("/sms")
    async def sms_webhook(request: Request) -> JSONResponse:
        """Handle incoming SMS webhooks from Twilio."""
        try:
            form_data = await request.json()
            webhook_data = dict(form_data)

            # Debug: Log the raw webhook data to see what Twilio is sending
            logger.debug(f"Received webhook data: {webhook_data}")

            sms_channel.process_webhook(webhook_data)
            return JSONResponse(content={"status": "ok"}, status_code=200)

        except Exception as e:
            logger.error(f"Error processing SMS webhook: {str(e)}")
            return JSONResponse(content={"status": "error", "message": str(e)}, status_code=400)

    # Start the server
    logger.info("Starting TAF SMS Server on 0.0.0.0:8000")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
