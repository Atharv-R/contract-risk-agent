"""
LLM Wrapper — Handles all communication with Google Gemini.

Provides a clean interface with:
  - Automatic .env loading for the API key
  - Retry logic for transient failures
  - JSON response parsing (Gemini sometimes wraps JSON in code blocks)
  - Rate limiting to stay within free tier (15 requests/minute)
"""

"""
LLM Wrapper — Supports multiple providers with automatic fallback.

Provider priority:
  1. Whatever LLM_PROVIDER is set to in .env (groq or gemini)
  2. Falls back to the other if the primary fails

Groq free tier:  30 requests/min, runs Llama 3.3 70B — excellent for analysis.
Gemini free tier: 15 requests/min, runs Gemini 2.0 Flash.
"""

import os
import re
import json
import time

from dotenv import load_dotenv

load_dotenv()


# ── Provider: Groq ───────────────────────────────────────────────

def _call_groq(
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> str:
    """Call Groq's API (Llama 3.3 70B)."""
    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set in .env")

    client = Groq(api_key=api_key)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    # Models to try in order
    models = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "gemma2-9b-it",
    ]

    for model in models:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "not exist" in error_msg:
                continue  # Try next model
            raise  # Re-raise rate limits and other errors

    raise RuntimeError("All Groq models failed")


# ── Provider: Gemini ─────────────────────────────────────────────

def _call_gemini(
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> str:
    """Call Google Gemini API."""
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in .env")

    client = genai.Client(api_key=api_key)

    config = types.GenerateContentConfig(
        system_instruction=system_prompt if system_prompt else None,
        temperature=temperature,
        max_output_tokens=max_tokens,
    )

    models = ["gemini-2.0-flash", "gemini-2.0-flash-lite"]

    for model in models:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
            return response.text
        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "404" in error_msg:
                continue
            raise

    raise RuntimeError("All Gemini models failed")


# ── Main Entry Point ─────────────────────────────────────────────

def call_gemini(
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.1,
    max_tokens: int = 4096,
    retries: int = 3,
) -> str:
    """
    Send a prompt to an LLM. Tries the preferred provider first,
    then falls back to the other.

    The function is still called call_gemini for backward compatibility
    but it routes to whichever provider is configured.
    """
    # Determine provider order
    preferred = os.getenv("LLM_PROVIDER", "groq").lower()

    if preferred == "groq":
        providers = [("groq", _call_groq), ("gemini", _call_gemini)]
    else:
        providers = [("gemini", _call_gemini), ("groq", _call_groq)]

    last_error = None

    for provider_name, provider_fn in providers:
        for attempt in range(retries):
            try:
                result = provider_fn(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return result

            except Exception as e:
                last_error = e
                error_msg = str(e).lower()

                # Print error on first attempt
                if attempt == 0:
                    print(f"  ⚠️  {provider_name} error: {str(e)[:120]}")

                # Rate limited — wait and retry
                if "429" in error_msg or "rate" in error_msg or "resource" in error_msg or "quota" in error_msg:
                    wait_time = (attempt + 1) * 10
                    print(f"  ⏳ Rate limited ({provider_name}). Waiting {wait_time}s... ({attempt + 1}/{retries})")
                    time.sleep(wait_time)
                    continue

                # Auth or config error — skip to next provider
                if any(x in error_msg for x in ["api_key", "auth", "not set", "invalid"]):
                    print(f"  → {provider_name} auth issue, trying next provider...")
                    break

                # Other error — short retry
                if attempt < retries - 1:
                    time.sleep(3)
                    continue
                break

    raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")


# ── JSON Parsing ─────────────────────────────────────────────────

def parse_json_response(text: str) -> dict:
    """Extract JSON from an LLM response, handling code blocks and noise."""
    text = text.strip()

    # Try 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try 2: Extract from markdown code block
    code_block_match = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try 3: Find any JSON object in the text
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    return {
        "error": "Failed to parse LLM response as JSON",
        "raw_response": text[:500],
    }


# ── Direct Testing ───────────────────────────────────────────────

if __name__ == "__main__":
    from rich import print as rprint
    from rich.panel import Panel

    rprint(Panel("[bold]LLM Provider Test[/bold]", style="blue"))

    # Show which provider is configured
    provider = os.getenv("LLM_PROVIDER", "groq")
    rprint(f"  Preferred provider: [yellow]{provider}[/yellow]")
    rprint(f"  GROQ_API_KEY:   {'[green]set[/green]' if os.getenv('GROQ_API_KEY') else '[red]not set[/red]'}")
    rprint(f"  GEMINI_API_KEY: {'[green]set[/green]' if os.getenv('GEMINI_API_KEY') else '[red]not set[/red]'}")

    # Test the call
    rprint(f"\n  Sending test prompt...")
    try:
        response = call_gemini(
            prompt='Analyze this short clause and respond with JSON: {"risk": "low", "reason": "standard boilerplate"}\n\nClause: "This agreement is effective as of January 1, 2025."',
            system_prompt="You are a contract analyst. Respond with valid JSON only.",
            retries=2,
        )
        parsed = parse_json_response(response)
        rprint(f"\n  [green]✓ LLM is working![/green]")
        rprint(f"  Provider used: {provider}")
        rprint(f"  Response: {parsed}")
    except Exception as e:
        rprint(f"\n  [red]✗ Failed: {e}[/red]")
        rprint(f"\n  Troubleshooting:")
        rprint(f"  1. Get a free Groq key: https://console.groq.com/keys")
        rprint(f"  2. Add to .env: GROQ_API_KEY=your_key_here")
        rprint(f"  3. Add to .env: LLM_PROVIDER=groq")