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
from taf.core.config import TwilioMemoryConfig
from taf.core.context import ConversationSession
from taf.models.memory import MemoryRetrievalResponse

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

    # Add user message to history
    user_msg: ChatCompletionUserMessageParam = {"role": "user", "content": user_message}
    conversation_messages[conv_id].append(user_msg)

    # Generate response with OpenAI
    client = openai.AsyncOpenAI()
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
    # Initialize TAF
    # Memory service is optional - only include if environment variable is set
    memory_store_id = os.environ.get("MEMORY_STORE_ID")
    twilio_memory_config = (
        TwilioMemoryConfig(memory_store_id=memory_store_id) if memory_store_id else None
    )

    taf = TAF(
        config=TAFConfig(
            environment=os.environ["ENVIRONMENT"],
            conversation_service_sid=os.environ["CONVERSATION_SERVICE_SID"],
            twilio_account_sid=os.environ["TWILIO_ACCOUNT_SID"],
            twilio_auth_token=os.environ["TWILIO_AUTH_TOKEN"],
            twilio_phone_number=os.environ["TWILIO_PHONE_NUMBER"],
            twilio_memory_config=twilio_memory_config,
        )
    )

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
            # Twilio sends form-encoded data, not JSON
            form_data = await request.form()
            webhook_data = dict(form_data)
            sms_channel.process_webhook(webhook_data)
            return JSONResponse(content={"status": "ok"}, status_code=200)

        except Exception as e:
            logger.error(f"Error processing SMS webhook: {str(e)}")
            return JSONResponse(content={"status": "error", "message": str(e)}, status_code=400)

    # Start the server
    logger.info("Starting TAF SMS Server on 0.0.0.0:8000")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
