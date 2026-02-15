"""
LLM integration module for Language-Learning Chatbot
Uses OpenRouter API with Xiaomi MIMO v2 Flash model
"""

import os
import httpx
import json
import asyncio
import yaml
from typing import List, Dict, Optional, Union
from datetime import datetime

# OpenRouter API configuration
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
#MODEL_NAME = "xiaomi/mimo-v2-flash:free"
#MODEL_NAME = "nvidia/nemotron-3-nano-30b-a3b:free"
MODEL_NAME = "openai/gpt-oss-120b:free"

# Load system prompts from YAML file
def _load_prompts() -> Dict[str, Dict]:
    """Load system prompts from prompts.yaml file"""
    prompts_file = os.path.join(os.path.dirname(__file__), "prompts.yaml")
    try:
        with open(prompts_file, 'r', encoding='utf-8') as f:
            prompts = yaml.safe_load(f)
        return prompts
    except FileNotFoundError:
        print(f"Warning: prompts.yaml not found at {prompts_file}")
        return {}
    except yaml.YAMLError as e:
        print(f"Error parsing prompts.yaml: {e}")
        return {}

# Initialize prompts
SYSTEM_PROMPTS = _load_prompts()

async def generate_reply(
    messages: List[Dict],
    target_lang: str,
    mode: str = "chat",
    is_primary_lang: bool = True,
    system_prompt: Optional[str] = None
) -> str:
    """
    Generate a reply using OpenRouter API

    Args:
        messages: List of message dicts with 'role' and 'text' keys
        target_lang: Target language code (e.g., 'en', 'de', 'fr', 'es')
        mode: 'chat' or 'tutor'
        is_primary_lang: Whether the language is primary (learning) or secondary (native)
        system_prompt: Custom system prompt (optional)

    Returns:
        Assistant response text
    """
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY environment variable not set")

    # Select system prompt based on mode and language
    if system_prompt is None:
        lang_code = target_lang.lower()
        if lang_code in SYSTEM_PROMPTS:
            lang_prompts = SYSTEM_PROMPTS[lang_code]
            if mode == "tutor" and "tutor" in lang_prompts:
                system_prompt = lang_prompts["tutor"]
            elif mode == "chat":
                # Select chat_primary or chat_secondary based on is_primary_lang
                if is_primary_lang and "chat_primary" in lang_prompts:
                    system_prompt = lang_prompts["chat_primary"]
                elif not is_primary_lang and "chat_secondary" in lang_prompts:
                    system_prompt = lang_prompts["chat_secondary"]
                elif "chat" in lang_prompts:
                    # Fallback to old "chat" key if specific ones don't exist
                    system_prompt = lang_prompts["chat"]
        
        # Fallback to English if language not found
        if system_prompt is None:
            if mode == "tutor" and "en" in SYSTEM_PROMPTS and "tutor" in SYSTEM_PROMPTS["en"]:
                system_prompt = SYSTEM_PROMPTS["en"]["tutor"]
            elif mode == "chat":
                if is_primary_lang and "en" in SYSTEM_PROMPTS and "chat_primary" in SYSTEM_PROMPTS["en"]:
                    system_prompt = SYSTEM_PROMPTS["en"]["chat_primary"]
                elif not is_primary_lang and "en" in SYSTEM_PROMPTS and "chat_secondary" in SYSTEM_PROMPTS["en"]:
                    system_prompt = SYSTEM_PROMPTS["en"]["chat_secondary"]
                else:
                    system_prompt = SYSTEM_PROMPTS.get("en", {}).get("chat", "You are a helpful language tutor.")

    # Prepare messages for OpenRouter API
    api_messages = [
        {"role": "system", "content": system_prompt}
    ]
    print(f"Using system prompt for {target_lang} ({mode}, primary={is_primary_lang}):\n{system_prompt}\n")
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
        target_lang: Target language code (e.g., 'en', 'de', 'fr', 'es')

    Returns:
        Translated text string or list of strings
    """
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY environment variable not set")

    # Get translator prompt for target language
    lang_code = target_lang.lower()
    if lang_code in SYSTEM_PROMPTS and "translator" in SYSTEM_PROMPTS:
        system_prompt = SYSTEM_PROMPTS["translator"].get(lang_code, SYSTEM_PROMPTS["translator"].get("en", "You are a professional translator."))
    else:
        system_prompt = SYSTEM_PROMPTS.get("translator", {}).get("en", "You are a professional translator.")

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
                        translated_text = choice['message']['content'].strip()
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


async def generate_conversation_starters_from_posts(
    posts: List[Dict],
    desired_count: int = 6,
    target_lang: str = "en"
) -> List[Dict]:
    """Use the LLM to craft conversation starters from Reddit posts."""
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY environment variable not set")
    if not posts:
        raise ValueError("No Reddit posts available to generate starters.")

    limited_posts = posts[:20]
    post_lines = []
    for idx, post in enumerate(limited_posts, start=1):
        title = post.get("title", "Untitled")
        subreddit = post.get("subreddit", "unknown")
        summary = (post.get("selftext") or "")[:280].replace("\n", " ").strip()
        post_lines.append(
            f"{idx}. [r/{subreddit}] {title} (score {post.get('score', 0)}) "
            f"Summary: {summary or 'No description provided.'}"
        )

    posts_block = "\n".join(post_lines)
    system_prompt = (
        "You craft engaging conversation starters for a language learning chatbot. "
        "Each starter should help a user begin a conversation in a friendly, curious tone. "
        "Return only valid JSON."
    )
    user_prompt = (
        f"Create up to {desired_count} unique conversation starters in {target_lang.upper()} "
        "based on the Reddit trends below. Each starter object must include:\n"
        '  - "title": short catchy title under 60 characters\n'
        '  - "assistant_opening": 2-3 sentences the AI assistant will say to begin the chat\n'
        '  - "subreddit": subreddit name (e.g., technology)\n'
        '  - "source_url": optional reddit link if helpful\n'
        "Keep tone positive and inclusive. Use general phrasing that works for broad audiences.\n\n"
        f"Reddit posts:\n{posts_block}\n\n"
        "Respond with a JSON array only."
    )

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 700,
        "top_p": 0.9,
    }

    try:
        async with httpx.AsyncClient(timeout=40.0) as client:
            response = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/mofadiheh/tutors-nightmare",
                    "X-Title": "Language Learning Chatbot",
                },
                json=payload,
            )
            if response.status_code != 200:
                raise Exception(
                    f"Conversation starter generation failed: {response.status_code} {response.text}"
                )
            data = response.json()
            content = data["choices"][0]["message"]["content"]
    except httpx.TimeoutException:
        raise Exception("Conversation starter request timed out")
    except httpx.RequestError as exc:
        raise Exception(f"Conversation starter network error: {exc}")

    json_payload = _extract_json_array(content)
    starters_raw = json.loads(json_payload)
    if not isinstance(starters_raw, list):
        raise ValueError("Unexpected starter payload format")

    sanitized = []
    for entry in starters_raw:
        title = (entry.get("title") or "").strip()
        opening = (entry.get("assistant_opening") or "").strip()
        if not title or not opening:
            continue
        sanitized.append(
            {
                "title": title,
                "assistant_opening": opening,
                "subreddit": entry.get("subreddit"),
                "source_url": entry.get("source_url"),
                "metadata": {
                    "raw_source": entry.get("source_reference"),
                },
            }
        )
        if len(sanitized) >= desired_count:
            break

    if not sanitized:
        raise ValueError("LLM returned no usable conversation starters.")
    return sanitized


def _extract_json_array(text: str) -> str:
    """Extract the first JSON array from a text blob."""
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON array detected in model response.")
    return text[start : end + 1]
