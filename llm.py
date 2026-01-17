"""
LLM integration module for Language-Learning Chatbot
Uses OpenRouter API with Xiaomi MIMO v2 Flash model
"""

import os
import httpx
import json
import asyncio
from typing import List, Dict, Optional, Union
from datetime import datetime

# OpenRouter API configuration
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
#MODEL_NAME = "xiaomi/mimo-v2-flash:free"
MODEL_NAME = "nvidia/nemotron-3-nano-30b-a3b:free"

# System prompts for different modes
CHAT_SYSTEM_PROMPT = """You are a helpful language tutor. Have natural conversations and gently correct mistakes.
Respond in {target_lang}. Keep responses conversational and engaging."""

TUTOR_SYSTEM_PROMPT = """You are a language tutor answering questions about vocabulary, grammar, and language usage.
Be clear and educational. Respond in {target_lang}. Focus on teaching and explaining concepts."""

TRANSLATOR_SYSTEM_PROMPT = """You are a professional translator. Translate the given text accurately into {target_lang}. 
Only provide the translated text without additional commentary."""

async def generate_reply(
    messages: List[Dict],
    target_lang: str,
    mode: str = "chat",
    system_prompt: Optional[str] = None
) -> str:
    """
    Generate a reply using OpenRouter API

    Args:
        messages: List of message dicts with 'role' and 'text' keys
        target_lang: Target language code (e.g., 'es', 'fr')
        mode: 'chat' or 'tutor'
        system_prompt: Custom system prompt (optional)

    Returns:
        Assistant response text
    """
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY environment variable not set")

    # Select system prompt based on mode
    if system_prompt is None:
        if mode == "tutor":
            system_prompt = TUTOR_SYSTEM_PROMPT.format(target_lang=target_lang.upper())
        else:
            system_prompt = CHAT_SYSTEM_PROMPT.format(target_lang=target_lang.upper())

    # Prepare messages for OpenRouter API
    api_messages = [
        {"role": "system", "content": system_prompt}
    ]

    # Add conversation history (limit to last 20 messages to avoid token limits)
    recent_messages = messages[-20:] if len(messages) > 20 else messages

    for msg in recent_messages:
        role = msg.get('role', 'user')
        text = msg.get('text', '')

        # Map our roles to OpenRouter roles
        if role == 'user':
            api_role = 'user'
        elif role == 'assistant':
            api_role = 'assistant'
        else:
            continue  # Skip unknown roles

        api_messages.append({
            "role": api_role,
            "content": text
        })

    # Prepare API request
    payload = {
        "model": MODEL_NAME,
        "messages": api_messages,
        "temperature": 0.7,
        "max_tokens": 500,
        "top_p": 0.9
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/mofadiheh/tutors-nightmare",
                    "X-Title": "Language Learning Chatbot"
                },
                json=payload
            )

            if response.status_code != 200:
                error_text = response.text
                print(f"OpenRouter API error: {response.status_code} - {error_text}")
                raise Exception(f"API request failed: {response.status_code}")

            data = response.json()

            # Extract the assistant response
            if 'choices' in data and len(data['choices']) > 0:
                choice = data['choices'][0]
                if 'message' in choice and 'content' in choice['message']:
                    return choice['message']['content'].strip()

            print(f"Unexpected API response format: {data}")
            raise Exception("Invalid API response format")

    except httpx.TimeoutException:
        print("OpenRouter API request timed out")
        raise Exception("Request timed out - please try again")

    except httpx.RequestError as e:
        print(f"OpenRouter API request error: {e}")
        raise Exception(f"Network error: {str(e)}")

    except json.JSONDecodeError as e:
        print(f"Failed to parse API response: {e}")
        raise Exception("Invalid response from API")

    except Exception as e:
        print(f"Unexpected error in generate_reply: {e}")
        raise Exception(f"LLM generation failed: {str(e)}")

async def translate_text(text: Union[str, List[str]], target_lang: str) -> Union[str, List[str]]:
    """
    Translate text using OpenRouter API

    Args:
        text: Text string or list of strings to translate
        target_lang: Target language code (e.g., 'es', 'fr')

    Returns:
        Translated text string or list of strings
    """
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY environment variable not set")

    system_prompt = TRANSLATOR_SYSTEM_PROMPT.format(target_lang=target_lang.upper())

    async def _translate_one(t: str) -> str:
        api_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": t}
        ]

        payload = {
            "model": MODEL_NAME,
            "messages": api_messages,
            "temperature": 0.0,
            "max_tokens": 1000
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{OPENROUTER_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/mofadiheh/tutors-nightmare",
                        "X-Title": "Language Learning Chatbot"
                    },
                    json=payload
                )

                if response.status_code != 200:
                    error_text = response.text
                    print(f"OpenRouter API error (translate): {response.status_code} - {error_text}")
                    raise Exception(f"API request failed: {response.status_code}")

                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    choice = data['choices'][0]
                    if 'message' in choice and 'content' in choice['message']:
                        return choice['message']['content'].strip()

                print(f"Unexpected API response format (translate): {data}")
                raise Exception("Invalid API response format")

        except httpx.TimeoutException:
            print("OpenRouter API translate request timed out")
            raise Exception("Request timed out - please try again")
        except httpx.RequestError as e:
            print(f"OpenRouter API translate request error: {e}")
            raise Exception(f"Network error: {str(e)}")
        except json.JSONDecodeError as e:
            print(f"Failed to parse translate API response: {e}")
            raise Exception("Invalid response from API")

    if isinstance(text, str):
        return await _translate_one(text)
    else:
        # Translate list of strings concurrently, preserve order
        tasks = [_translate_one(t) for t in text]
        results = await asyncio.gather(*tasks)
        return results


async def test_llm_connection() -> bool:
    """
    Test the LLM connection with a simple request
    Returns True if successful, False otherwise
    """
    try:
        test_messages = [
            {"role": "user", "text": "Hello, can you respond in English?"}
        ]
        response = await generate_reply(test_messages, "en", "chat")
        return len(response.strip()) > 0
    except Exception as e:
        print(f"LLM connection test failed: {e}")
        return False


def get_model_info() -> Dict:
    """Get information about the current model configuration"""
    return {
        "provider": "OpenRouter",
        "model": MODEL_NAME,
        "api_key_set": bool(OPENROUTER_API_KEY),
        "base_url": OPENROUTER_BASE_URL
    }
